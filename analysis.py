#!/bin/bash
# Analysis Pipeline: Access FASTQ files, Trimming, Mapping, Sorting, Primer Trimming, and Consensus Calling

# Define reference files
REFERENCE_FASTA="/home/<user>/Analysis/genome_ref/reference.fasta"
PRIMER_BED="/home/<user>/Analysis/genome_ref/mtDNA.bed"
ADAPTERS="/home/<user>/mambaforge/envs/mt-analysis/share/trimmomatic-0.39-2/adapters/adapters.fa"

# Define raw reads directory
RAW_READS_DIR="/home/<user>/Analysis/raw_reads"

# Ensure necessary directories exist
mkdir -p trimmed bams trimmed_bams sorted_bams consensus

echo "Starting pipeline..."

############################
# Step 0: Verify and Access FASTQ Files
############################
echo "Step 0: Checking for raw FASTQ files in ${RAW_READS_DIR}..."
if [ ! -d "$RAW_READS_DIR" ]; then
    echo "Error: Directory ${RAW_READS_DIR} not found!"
    exit 1
fi

# Move into the raw_reads directory to process files
cd ${RAW_READS_DIR}
FASTQ_FILES=(*_R1_001.fastq.gz)
if [ ${#FASTQ_FILES[@]} -eq 0 ]; then
    echo "Error: No FASTQ files found in ${RAW_READS_DIR}!"
    exit 1
fi
echo "FASTQ files found. Proceeding with processing..."

############################
# Step 1: Trim Raw FASTQ Files
############################
echo "Step 1: Trimming raw FASTQ files..."
for i in *_R1_001.fastq.gz
do
    base=$(basename ${i} _R1_001.fastq.gz)
    echo "Trimming ${base}..."
    
    trimmomatic PE ${i} ${base}_R2_001.fastq.gz \
                 ../trimmed/${base}_R1_pair.fastq.gz ../trimmed/${base}_R1_unpair.fastq.gz \
                 ../trimmed/${base}_R2_pair.fastq.gz ../trimmed/${base}_R2_unpair.fastq.gz \
                 ILLUMINACLIP:${ADAPTERS}:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:25
done
echo "Trimming completed!"

# Move back to the main directory
cd ..

############################
# Step 2: Align Reads and Sort BAM Files
############################
echo "Step 2: Mapping reads with BWA and sorting BAMs..."
for r1_file in trimmed/*_R1_pair.fastq.gz
do
    base=$(basename ${r1_file} _R1_pair.fastq.gz)
    r2_file="trimmed/${base}_R2_pair.fastq.gz"
    output_bam="bams/${base}.sorted.bam"

    echo "Mapping ${base}..."
    bwa mem -t 4 ${REFERENCE_FASTA} ${r1_file} ${r2_file} | samtools sort -o ${output_bam}
done
echo "Mapping completed!"

############################
# Step 3: Trim Primers Using iVar
############################
echo "Step 3: Trimming primers using iVar..."
for bam_file in bams/*.sorted.bam
do
    output_trimmed_bam="trimmed_bams/$(basename ${bam_file}).primertrim.bam"
    
    echo "Trimming primers in ${bam_file}..."
    ivar trim -e -i ${bam_file} -b ${PRIMER_BED} -p ${output_trimmed_bam}
done
echo "Primer trimming completed!"

############################
# Step 4: Sort Trimmed BAM Files
############################
echo "Step 4: Sorting trimmed BAM files..."
for trimmed_bam_file in trimmed_bams/*.primertrim.bam
do
    sorted_trimmed_bam="sorted_bams/$(basename ${trimmed_bam_file}).sorted.bam"
    
    echo "Sorting ${trimmed_bam_file}..."
    samtools sort ${trimmed_bam_file} -o ${sorted_trimmed_bam}
done
echo "Sorting completed!"

############################
# Step 5: Generate Consensus Sequences
############################
echo "Step 5: Generating consensus sequences with iVar..."
for sorted_bam_file in sorted_bams/*.sorted.bam
do
    consensus_output="consensus/$(basename ${sorted_bam_file}).consensus.fa"

    echo "Generating consensus for ${sorted_bam_file}..."
    samtools mpileup -A -d 1000 -B -Q 0 --reference ${REFERENCE_FASTA} ${sorted_bam_file} | ivar consensus -p ${consensus_output} -q 20 -t 0.9 -n N -m 100
done
echo "Consensus generation completed!"

echo "Pipeline finished successfully!"
