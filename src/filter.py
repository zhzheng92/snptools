# -*- coding: utf-8 -*-
"""
Created on Wed May 27 14:47:00 2015

@author: aaron
"""

import sys
import argparse
import textwrap
import timeit
import os

#########################################################
#### Need to add retention list filtering for DSF and PED
#########################################################

###############################################################################
def warning(*objs):
    print("WARNING: ", *objs, end='\n', file=sys.stderr)
    sys.exit()

###############################################################################
def version():
   v0 = """
   ############################################################################
   filter
   (c) 2015 Aaron Kusmec
   
   Filter SNPs based on missing rates/minor allele frequencies.
   Input modes,
       1 = .dsf
       2 = .hmp.txt
       3 = .ped (PLINK)
       
   Usage: python3 filter.py -s example.stat -i example.dsf -o filtered -m 1 -n 0.6 -f 0.05
   
   NOTE1: Retaining SNPs through a SNP list is currently only supported for HMP
          files.
   NOTE2: Using a SNP list cannot currently be combined with MAF/miss filtering.
       
   ############################################################################
   """
   
   return v0

###############################################################################  
def get_parser():
    parser = argparse.ArgumentParser(
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description = textwrap.dedent(version()))

    parser.add_argument('-p', '--path', help = 'Path of the input file', \
                        nargs = '?', default = os.getcwd())
    parser.add_argument('-s', '--stat', help = 'Stat file', type = str)
    parser.add_argument('-i', '--input', help = 'Input file', type = str)
    parser.add_argument('-o', '--output', help = 'Output file (no ext)', type = str)
    parser.add_argument('-m', '--mode', help = 'I/O mode', type = int)
    parser.add_argument('-n', '--miss', help = 'Max missing rate', \
                        type = float, default = 1.0)
    parser.add_argument('-f', '--maf', help = 'Minimum minor allele frequency',\
                        type = float, default = 0.0)
    parser.add_argument('-r', '--retain', help = 'List of SNPs to retain', type = str, default = None)

    return parser

###############################################################################
def checkFile(filename, mode):
    print("Checking [ ", filename, " ].")
    
    with open(filename, 'r') as infile:
        line = infile.readline().split()
    
    if mode == 1:
        if line[0] != "snpid" or line[1] != "major" or line[2] != "minor":
            warning(".dsf formatted incorrectly.")
    elif mode == 2:
        if line[0] != "rs" and line[0] != "rs#":
            warning(".hmp.txt formatted incorrectly.")
    elif mode == 3:
        if len(line) <= 6:
            warning(".ped missing genotypes.")
            
        # Check the map file as well
        with open(filename.split('.')[0] + ".map", 'r') as infile:
            line = infile.readline().split()
        if len(line) != 4:
            warning(".map incorrectly formatted.")
    else:
        warning("Unrecognized file format.")
    
    print("[ ", filename, " ] is appropriately formatted.")

###############################################################################
def getStats(filename):
    print("Reading [ ", filename, " ].")
    
    stats = {}
    with open(filename, 'r') as infile:
        header = infile.readline()
        for line in infile:
            line = line.split()
            stats[line[0]] = [float(line[5]), float(line[6])]

    return stats

###############################################################################
def filterDsf(inname, outname, stats, miss, maf):
    print("Filtering [ ", inname, " ].")

    infile = open(inname, 'r')
    keepfile = open(outname + ".dsf", 'w')
    filtfile = open(outname + "_filtered.dsf", 'w')

    header = infile.readline().split()
    keepfile.write('\t'.join(header) + '\n')
    filtfile.write('\t'.join(header) + '\n')
    
    kept = filt = counter = 0
    for snp in infile:
        snp = snp.split()
        if snp[0] not in stats:
            warning(snp[0] + " is not present in .stat file.")

        # Filter or keep
        if stats[snp[0]][0] <= miss and stats[snp[0]][1] >= maf:
            keepfile.write('\t'.join(snp) + '\n')
            kept += 1
        else:
            filtfile.write('\t'.join(snp) + '\n')
            filt += 1
        
        counter += 1
        if counter % 1e5 == 0:
            print("Processed [ ", str(counter), " ] SNPs.")

    infile.close()
    keepfile.close()
    filtfile.close()

    print("Kept [ ", str(kept), " ] SNPs in [ ", outname + ".dsf", " ].")
    print("Removed [ ", str(filt), " ] SNPs to [ ", outname + "_filtered.dsf", " ].")

###############################################################################
def filterHmp(inname, outname, stats, miss, maf, retain):
    print("Filtering [ ", inname, " ].")

    infile = open(inname, 'r')
    keepfile = open(outname + ".hmp.txt", 'w')
    filtfile = open(outname + "_filtered.hmp.txt", 'w')

    header = infile.readline().split()
    keepfile.write('\t'.join(header) + '\n')
    filtfile.write('\t'.join(header) + '\n')

    kept = filt = counter = 0
    for snp in infile:
        snp = snp.split()
        if snp[0] not in stats:
            warning(snp[0] + " is not present in .stat file.")
        
        if retain is not None:
            if snp[0] in retain:
                keepfile.write('\t'.join(snp) + '\n')
                kept += 1
            else:
                filtfile.write('\t'.join(snp) + '\n')
                filt += 1
        else:
            # Filter or keep
            if stats[snp[0]][0] <= miss and stats[snp[0]][1] >= maf:
                keepfile.write('\t'.join(snp) + '\n')
                kept += 1
            else:
                filtfile.write('\t'.join(snp) + '\n')
                filt += 1
        
        counter += 1
        if counter % 1e5 == 0:
            print("Processed [ ", str(counter), " ] SNPs.")

    infile.close()
    keepfile.close()
    filtfile.close()

    print("Kept [ ", str(kept), " ] SNPs in [ ", outname + ".hmp.txt", " ].")
    print("Removed [ ", str(filt), " ] SNPs to [ ", outname + "_filtered.hmp.txt", " ].")

###############################################################################
def filterPed(inname, outname, stats, miss, maf):
    # Read the .map file and verify that it contains the same SNPs
    #  as the .stat file.
    mapname = inname.split('.')[0] + ".map"
    print("Verifying [ ", mapname, " ].")
    smap = []
    with open(mapname, 'r') as mapfile:
        for line in mapfile:
            line = line.split()
            if line[1] in stats:
                smap.append(line)
            else:
                warning(line[1] + " is not present in .stat file.")

    # Read the entire .ped file into memory and transpose
    snps = []
    print("Reading [ ", inname, " ].")
    with open(inname, 'r') as infile:
        for line in infile:
            snps.append(line.strip().split('\t'))
    snps = zip(*snps)

    # Setup the output lists and process the metadata
    ksnps = []; kmap = []
    fsnps = []; fmap = []

    for _ in range(6):
        m = next(snps)
        ksnps.append(m)
        fsnps.append(m)

    # Filter or keep
    kept = filt = counter = 0
    for index, value in enumerate(snps):
        if stats[smap[index][1]][0] <= miss and stats[smap[index][1]][1] >= maf:
            ksnps.append(value)
            kmap.append(smap[index])
            kept += 1
        else:
            fsnps.append(value)
            fmap.append(smap[index])
            filt += 1

        counter += 1
        if counter % 1e5 == 0:
            print("Processed [ ", str(counter), " ] SNPs.")

    # Report the results and write the output
    print("Kept [ ", str(kept), " ] SNPs in [ ", outname + ".ped", " ].")
    ksnps = zip(*ksnps)
    with open(outname + ".ped", 'w') as outfile:
        for k in ksnps:
            outfile.write('\t'.join(k) + '\n')

    with open(outname + ".map", 'w') as outfile:
        for k in kmap:
            outfile.write('\t'.join(k) + '\n')

    print("Removed [ ", str(filt), " ] SNPs to [ ", outname + "_filtered.ped", " ].")
    fsnps = zip(*fsnps)
    with open(outname + "_filtered.ped", 'w') as outfile:
        for f in fsnps:
            outfile.write('\t'.join(f) + '\n')

    with open(outname + "_filtered.map", 'w') as outfile:
        for f in fmap:
            outfile.write('\t'.join(f) + '\n')

###############################################################################
def getRetain(filename):
    retain = {}
    with open(filename, 'r') as infile:
        for line in infile:
            retain[line.strip()] = True
    return retain

###############################################################################
if __name__ == '__main__':
    parser = get_parser()
    args = vars(parser.parse_args())
    
    # Change the working directory if necessary
    if args['path'] is not None:
        os.chdir(args['path'])
    if args['input'] is None:
        warning("No input file.")
    if args['output'] is None:
        warning("No output file.")
    
    print(version())
    
    st = timeit.default_timer()
    
    # Check input file
    checkFile(args['input'], args['mode'])

    stats = getStats(args['stat'])
    if args['retain'] is not None:
        retain = getRetain(args['retain'])
    else:
        retain = None

    if args['mode'] == 1:
        filterDsf(args['input'], args['output'], stats, args['miss'], args['maf'])
    elif args['mode'] == 2:
        filterHmp(args['input'], args['output'], stats, args['miss'], args['maf'], retain)
    elif args['mode'] == 3:
        filterPed(args['input'], args['output'], stats, args['miss'], args['maf'])
    else:
        warning("Unrecognized input mode.")
    
    et = timeit.default_timer()

    print("Conversion finished.")
    print("Time: %.2f min." % ((et - st)/60))
