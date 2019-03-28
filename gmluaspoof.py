#!/usr/bin/env python3

from os.path import split, join, isfile, isdir
from os import listdir
from io import SEEK_SET, SEEK_END
from re import compile
from sys import argv
from lzma import LZMACompressor, LZMADecompressor, FORMAT_ALONE, FILTER_LZMA1
from struct import pack
from binascii import crc32

def print_usage():
	print( 'Usage: {0} <command> <file|directory>'.format( argv[0] ) )
	print( 'Commands:' )
	print( '\tcompress: compress file(s) and spoof crc if needed' )
	print( '\tdecompress: decompress file(s)' )

def compress( in_path, out_path, crc_to_spoof ):
	with open( in_path, 'rb' ) as in_file, open( out_path, 'wb' ) as out_file:
		lzmac = LZMACompressor( FORMAT_ALONE, filters = [ { 'id': FILTER_LZMA1, 'dict_size': 64 * 1024 } ] )
		
		size = 0
		crc = None
		
		out_file.write( pack( '<I', crc_to_spoof ) )
		
		_, file_name = split( in_path )
		data = '''
			do
				local f = file.Open( 'files.txt', 'ab', 'DATA' )
				if f then
					f:Write( string.format( '{0} = %s\\n', debug.getinfo( 1 ).short_src ) )
					f:Close()
				end
			end
		'''.format( file_name ).encode()
		data = in_file.read( 1024 )
		while len( data ):
			size = size + len( data )
			if crc == None:
				crc = crc32( data )
			else:
				crc = crc32( data, crc )
			out_file.write( lzmac.compress( data ) )
			data = in_file.read( 1024 )
			
		if crc != crc_to_spoof:
			fix = 0
			working_crc = ~crc_to_spoof
			
			for i in range( 32 ):
				if fix & 1:
					fix = ( fix >> 1 ) ^ 0xedb88320
				else:
					fix = fix >> 1
				
				if working_crc & 1:
					fix = fix ^ 0x5b358fd3
				
				working_crc = working_crc >> 1
			
			fix = ( fix ^ ~crc ) & 0xffffffff
			fix = pack( '<I', fix )
			#crc = crc32( fix, crc )
			size = size + len( fix )
			print( 'Fix: {0}'.format( fix ) )
			out_file.write( lzmac.compress( fix ) )
		
		out_file.write( lzmac.flush() )
		out_file.seek( 9, SEEK_SET )
		out_file.write( pack( '<q', size ) )
		
def decompress( in_path, out_path ):
	with open( in_path, 'rb' ) as in_file, open( out_path, 'wb' ) as out_file:
		lzmad = LZMADecompressor( FORMAT_ALONE )
		
		in_file.seek( 4, SEEK_SET )
		
		data = in_file.read( 1024 )
		while len( data ):
			out_file.write( lzmad.decompress( data ) )
			data = in_file.read( 1024 )
	
def main():
	if len( argv ) < 3:
		print_usage()
		return
	
	if argv[1] == 'compress':
		regex = compile( r'([0-9]+)\.src\.lua' )
		
		if isfile( argv[2] ):
			path, file_name = split( argv[2] )
			
			match = regex.match( file_name )
			if not match:
				return
			
			in_file_path = argv[2]
			out_file_path = join( path, match.group( 1 ) + '.lua' )
			crc_to_spoof = int( match.group( 1 ) )
			
			print( 'Compressing \'{0}\''.format( file_name ) )
				
			compress( in_file_path, out_file_path, crc_to_spoof )
		elif isdir( argv[2] ):
			file_names = listdir( argv[2] )
	
			# TODO: fix this, popping will move indices down making future pops pop wrong values
			#for i in range( len( file_names ) ):
			#	if not isfile( join( argv[2], file_names[i] ) ):
			#		file_names.pop( i )
			
			for file_name in file_names:
				match = regex.match( file_name )
				if not match:
					continue
					
				in_file_path = join( argv[2], file_name )
				out_file_path = join( argv[2], match.group( 1 ) + '.lua' )
				crc_to_spoof = int( match.group( 1 ) )
				
				print( 'Compressing \'{0}\''.format( file_name ) )
				
				compress( in_file_path, out_file_path, crc_to_spoof )
	elif argv[1] == 'decompress':
		regex = compile( r'([0-9]+)\.lua' )
		
		if isfile( argv[2] ):
			path, file_name = split( argv[2] )
			
			match = regex.match( file_name )
			if not match:
				return
			
			in_file_path = argv[2]
			out_file_path = join( path, match.group( 1 ) + '.src.lua' )
			
			if isfile( out_file_path ):
				return
			
			print( 'Decompressing \'{0}\''.format( file_name ) )
			
			decompress( in_file_path, out_file_path )
		elif isdir( argv[2] ):
			file_names = listdir( argv[2] )
		
			# TODO: fix this, popping will move indices down making future pops pop wrong values
			#for i in range( len( file_names ) ):
			#	if not isfile( join( argv[2], file_names[i] ) ):
			#		file_names.pop( i )
			
			for file_name in file_names:
				match = regex.match( file_name )
				if not match:
					continue
					
				in_file_path = join( argv[2], file_name )
				out_file_path = join( argv[2], match.group( 1 ) + '.src.lua' )
				
				if isfile( out_file_path ):
					continue
				
				print( 'Decompressing \'{0}\''.format( file_name ) )
				
				decompress( in_file_path, out_file_path )
	else:
		print_usage()

if __name__ == '__main__':
	main()
