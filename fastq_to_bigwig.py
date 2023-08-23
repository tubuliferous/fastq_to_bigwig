import argparse
import subprocess
import os

def run_command(command):
    """Run a shell command."""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Error executing command: {command}")
        print(stderr.decode())
        exit(1)

def get_base_name(filename):
    while '.' in filename:
        filename = os.path.splitext(filename)[0]
    return filename

def create_directory(path):
    """
    Create a directory specified by the given path.
    
    Args:
    - path (str): The path of the directory to be created.
    
    Returns:
    - None
    """
    try:
        os.mkdir(path)
        print(f"Directory {path} created successfully!")
    except FileExistsError:
        print(f"Directory {path} already exists.")
    except Exception as e:
        print(f"Error creating directory {path}. Reason: {e}")

def get_topmost_directory(path):
    # Split the path into its components
    parts = os.path.normpath(path).split(os.path.sep)
    # Return the first directory after the root, if available
    return parts[1] if len(parts) > 1 else None

def align_fastq(fastq_file, genome_file, aligner_path, output_prefix, cores):
    """Align FASTQ to produce a SAM file."""
    sam_file = output_prefix + ".sam"
    run_command(f"{aligner_path} -x {genome_file} -U {fastq_file} -S {sam_file} -p {cores}")
    return sam_file

def sam_to_bam(sam_file, output_prefix, cores):
    """Convert SAM to sorted BAM."""
    bam_file = output_prefix + ".sorted.bam"
    run_command(f"samtools view -@ {cores} -Sb {sam_file} | samtools sort -@ {cores} -o {bam_file}")
    return bam_file

def generate_bedgraph(bam_file, genome_file, output_prefix, cores):
    """Generate sorted BedGraph from BAM."""
    bedgraph_file = output_prefix + ".bedgraph"
    run_command(f"bedtools genomecov -bg -ibam {bam_file} -g {genome_file} | LC_COLLATE=C sort -k1,1 -k2,2n --parallel={cores} > {bedgraph_file}")
    return bedgraph_file

def bedgraph_to_bigwig(bedgraph_file, genome_file, output_prefix):
    """Convert BedGraph to BigWig."""
    chrom_sizes_file = os.path.join(get_topmost_directory(output_prefix), "chrom.sizes")
    print(chrom_sizes_file)
    run_command(f"cut -f1,2 {genome_file}.fai > {chrom_sizes_file}")
    bigwig_file = output_prefix + ".bw" 
    run_command(f"bedGraphToBigWig {bedgraph_file} {chrom_sizes_file} {bigwig_file}")
    return bigwig_file

def fastq_to_bigwig(fastq_file, genome_file, aligner_path, cores):
    """Pipeline to convert FASTQ to BigWig."""
    output_prefix = get_base_name(fastq_file)
    create_directory(output_prefix)
    output_prefix = os.path.join(output_prefix, output_prefix)
    sam_file = align_fastq(fastq_file, genome_file, aligner_path, output_prefix, cores)
    bam_file = sam_to_bam(sam_file, output_prefix, cores)
    bedgraph_file = generate_bedgraph(bam_file, genome_file, output_prefix, cores)
    bigwig_file = bedgraph_to_bigwig(bedgraph_file, genome_file, output_prefix)
    print(f"Done! BigWig file generated at: {bigwig_file}")

def download_and_convert_srr(srr_accession):
    """Download the given SRR accession using prefetch and convert to FASTQ."""
    print(f"  -> Downloading {srr_accession}.sra")
    run_command(f"prefetch {srr_accession}")
    fastq_file = f"{srr_accession}_1.fastq.gz"
    print(f"  -> Convert {srr_accession}.sra to FASTQ")
    run_command(f"fastq-dump --split-files -Z {srr_accession} | gzip > {fastq_file}")
    return fastq_file

def main():
    parser = argparse.ArgumentParser(description="Convert FASTQ or SRR to BigWig.")
    parser.add_argument("file_or_accession", help="Path to the FASTQ file or SRR accession.")
    parser.add_argument("genome_file", help="Path to the genome file.")
    parser.add_argument("aligner_path", help="Path to the aligner executable.")
    parser.add_argument("--cores", type=int, default=1, help="Number of cores to use for processing. Default is 1.")
    args = parser.parse_args()
    
    # Check if the provided file_or_accession is an SRR accession or a FASTQ file
    if ".fastq" in args.file_or_accession:
        fastq_file = args.file_or_accession
    else:
        print(f"Given input {args.file_or_accession} is treated as an SRR accession. Downloading and converting...")
        fastq_file = download_and_convert_srr(args.file_or_accession)

    fastq_to_bigwig(fastq_file, args.genome_file, args.aligner_path, args.cores)

if __name__ == "__main__":
    main()

# e.g. usage: python fastq_to_bigwig.py SRR20082645.fastq.gz resources/mm39/mm39 bowtie2 --cores 10
