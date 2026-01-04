use std::fs::File;
use std::io::{Read, BufReader, Write};

fn main() -> std::io::Result<()> {
    let input_path = "witness_part_core_0.tkbin";
    let output_path = "tests/data_input.cairo";
    
    let file = File::open(input_path)?;
    let mut reader = BufReader::new(file);
    let mut buffer = [0u8; 3];
    
    println!("[*] Extracting Stark-Witness from {}...", input_path);
    
    let mut cairo_array = String::from("array![");
    let mut count = 0;
    
    // We'll limit the first test to 5,000 steps to ensure snforge 
    // stays within the Pi 5's default memory limits
    while count < 5000 {
        if reader.read_exact(&mut buffer).is_err() { break; }
        // buffer[2] is our 'y' value from the Cython Turbo-Stride
        cairo_array.push_str(&format!("{}u8, ", buffer[2]));
        count += 1;
    }
    
    cairo_array.push_str("]");

    let mut out_file = File::create(output_path)?;
    write!(out_file, "fn get_test_data() -> Array<u8> {{ {} }}", cairo_array)?;

    println!("[+] Generated {} with {} steps.", output_path, count);
    Ok(())
}
