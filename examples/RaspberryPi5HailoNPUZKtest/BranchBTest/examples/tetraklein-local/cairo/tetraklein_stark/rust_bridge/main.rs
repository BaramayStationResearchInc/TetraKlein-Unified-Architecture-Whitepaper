use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use rayon::prelude::*;
use memmap2::Mmap;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let start = std::time::Instant::now();
    let test_dir = "/home/baramaystation1/TetraKlein/examples/tetraklein-local/tests";
    let max_total_steps = 50_000; 

    // Phase 1: Parallel Shard Discovery
    let mut shard_files: Vec<PathBuf> = fs::read_dir(test_dir)?
        .filter_map(|entry| entry.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().and_then(|s| s.to_str()) == Some("tkbin"))
        .collect();
    shard_files.sort();

    // Phase 2: Parallel Extraction
    // We collect into a Vec then truncate to satisfy Rayon's trait bounds
    let mut witness_y: Vec<u8> = shard_files
        .par_iter()
        .flat_map(|path| {
            read_shard_mmap(path, max_total_steps).unwrap_or_default()
        })
        .collect();
    
    witness_y.truncate(max_total_steps);

    // Phase 3: Segmented Cairo Generation
    let output_path = "../tests/test_contract/data_input.cairo";
    let mut writer = BufWriter::with_capacity(1024 * 1024, File::create(output_path)?);

    write_segmented_cairo(&mut writer, &witness_y)?;

    println!("[+] TetraKlein Stack: {} steps processed in {:.3}s", witness_y.len(), start.elapsed().as_secs_f64());
    Ok(())
}

fn read_shard_mmap(path: &Path, limit: usize) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let file = File::open(path)?;
    let mmap = unsafe { Mmap::map(&file)? };
    let mut y_values = Vec::new();
    // Only take up to the limit per shard to save memory
    for chunk in mmap.chunks_exact(3).take(limit) {
        y_values.push(chunk[2]);
    }
    Ok(y_values)
}

fn write_segmented_cairo(writer: &mut BufWriter<File>, data: &[u8]) -> Result<(), Box<dyn std::error::Error>> {
    writeln!(writer, "// TetraKlein High-Throughput Witness")?;
    
    // BREAKING DATA INTO CONSTANT SEGMENTS (2500 bytes each)
    let chunks: Vec<_> = data.chunks(2500).collect();

    for (i, chunk) in chunks.iter().enumerate() {
        writeln!(writer, "fn get_segment_{}() -> Span<u8> {{", i)?;
        write!(writer, "    let mut data = array![")?;
        for (j, val) in chunk.iter().enumerate() {
            if j % 20 == 0 { write!(writer, "\n        ")?; }
            write!(writer, "{}, ", val)?;
        }
        writeln!(writer, "\n    ];\n    data.span()\n}}")?;
    }

    // Final Assembly (Fixed the writeln! macro error)
    writeln!(writer, "pub fn get_test_data() -> Array<u8> {{")?;
    writeln!(writer, "    let mut data: Array<u8> = array![];")?;
    for i in 0..chunks.len() {
        writeln!(writer, "    let mut s_{} = get_segment_{}();", i, i)?;
        writeln!(writer, "    loop {{ match s_{}.pop_front() {{ Option::Some(v) => {{ data.append(*v); }}, Option::None => {{ break; }} }}; }};", i)?;
    }
    writeln!(writer, "    data\n}}")?;
    Ok(())
}
