#%% 
import os
import csv
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from PIL import Image, ExifTags
import xml.etree.ElementTree as ET
from xml.dom import minidom
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import exifread

def format_rational(value):
    """Safely converts Exif rational numbers (fractions) to strings."""
    if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
        if value.denominator == 0:
            return "0"
        if value.numerator == 1 and value.denominator > 1:
            return f"1/{value.denominator}"
        return str(round(value.numerator / value.denominator, 1))
    return str(value)

def format_exifread_ratio(tag_value):
    """Safely converts exifread Ratio objects to strings."""
    if hasattr(tag_value, 'num') and hasattr(tag_value, 'den'):
        if tag_value.den == 0:
            return "0"
        if tag_value.num == 1 and tag_value.den > 1:
            return f"1/{tag_value.den}"
        return str(round(tag_value.num / tag_value.den, 1))
    return str(tag_value)

def parse_exif_date(date_str):
    """Safely parses EXIF date strings into datetime objects."""
    if not date_str or date_str == 'Unknown':
        return None
    try:
        # EXIF dates are typically formatted as YYYY:MM:DD HH:MM:SS
        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
    except ValueError:
        return None

def get_detailed_metadata(image_path):
    """Extracts metadata using ExifRead (for RAWs) and Pillow (for generic image properties)."""
    meta = {
        'Image': {},
        'Camera': {}
    }
    
    # 1. Use ExifRead for Universal EXIF Data (RAWs and JPEGs)
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            
            width = tags.get('EXIF ExifImageWidth') or tags.get('Image ImageWidth')
            height = tags.get('EXIF ExifImageLength') or tags.get('Image ImageLength')
            if width and height:
                meta['Image']['Dimensions'] = f"{width} x {height}"
                meta['Image']['Width'] = str(width)
                meta['Image']['Height'] = str(height)

            if 'Image Make' in tags:
                meta['Camera']['Make'] = str(tags['Image Make']).strip()
            if 'Image Model' in tags:
                meta['Camera']['Model'] = str(tags['Image Model']).strip()
            
            dt = tags.get('EXIF DateTimeOriginal') or tags.get('Image DateTime')
            if dt:
                meta['Camera']['DateTimeOriginal'] = str(dt).strip()
                
            if 'EXIF FNumber' in tags:
                meta['Camera']['FStop'] = f"f/{format_exifread_ratio(tags['EXIF FNumber'].values[0])}"
            if 'EXIF ExposureTime' in tags:
                meta['Camera']['ExposureTime'] = f"{format_exifread_ratio(tags['EXIF ExposureTime'].values[0])} sec."
            if 'EXIF ISOSpeedRatings' in tags:
                meta['Camera']['ISOSpeed'] = f"ISO-{str(tags['EXIF ISOSpeedRatings']).strip()}"
            if 'EXIF FocalLength' in tags:
                meta['Camera']['FocalLength'] = f"{format_exifread_ratio(tags['EXIF FocalLength'].values[0])} mm"
    except Exception as e:
        print(f"ExifRead failed for {image_path.name}: {e}")

    # 2. Try Pillow for fallback dimensions and general image properties (BitDepth, DPI)
    try:
        with Image.open(image_path) as img:
            if 'Dimensions' not in meta['Image']:
                meta['Image']['Dimensions'] = f"{img.width} x {img.height}"
                meta['Image']['Width'] = str(img.width)
                meta['Image']['Height'] = str(img.height)
            
            dpi = img.info.get('dpi')
            if dpi:
                meta['Image']['HorizontalResolution'] = str(round(dpi[0]))
                meta['Image']['VerticalResolution'] = str(round(dpi[1]))
                
            mode_to_bpp = {'1': 1, 'L': 8, 'P': 8, 'RGB': 24, 'RGBA': 32, 'CMYK': 32, 'YCbCr': 24, 'I': 32, 'F': 32}
            meta['Image']['BitDepth'] = str(mode_to_bpp.get(img.mode, 'Unknown'))
    except Exception:
        pass 

    return meta

def prettify_xml(elem):
    """Returns a pretty-printed XML string."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

def process_directory(directory_path):
    """Generates an XML metadata catalog, a CSV report, and a coverage plot."""
    base_dir = Path(directory_path)
    
    if not base_dir.is_dir():
        print(f"Error: {directory_path} is not a valid directory.")
        return
        
    # NOTE: Switched to lowercase .nef so os.path.splitext(file)[1].lower() catches it
    valid_extensions = {'.jpg', '.jpeg', '.tif', '.tiff', '.png', '.nef'}
    print(f"Scanning {base_dir} for imagery (Single Pass)...")
    
    image_files = []
    folders = defaultdict(list)
    
    for root, _, files in os.walk(base_dir):
        current_folder = Path(root)
        for file in files:
            if os.path.splitext(file)[1].lower() in valid_extensions:
                img_path = current_folder / file
                image_files.append(img_path)
                folders[current_folder].append(img_path)
        
    if not image_files:
        print("No images found to process.")
        return

    extracted_dates = []
    csv_rows = []

    for folder_path, files in folders.items():
        files.sort() 
        
        # Check first image
        first_file = files[0]
        meta_first = get_detailed_metadata(first_file)
        dt_first = meta_first['Camera'].get('DateTimeOriginal', meta_first['Camera'].get('DateTime', 'Unknown'))
        if dt_first != 'Unknown':
            extracted_dates.append(dt_first)
            
        # Check last image
        last_file = files[-1]
        meta_last = get_detailed_metadata(last_file)
        dt_last = meta_last['Camera'].get('DateTimeOriginal', meta_last['Camera'].get('DateTime', 'Unknown'))
        if dt_last != 'Unknown':
            extracted_dates.append(dt_last)
            
        # Format folder path cleanly for the CSV
        try:
            rel_path = folder_path.relative_to(base_dir)
            folder_name = str(rel_path) if str(rel_path) != "." else "Root Directory"
        except ValueError:
            folder_name = str(folder_path)
            
        csv_rows.append([folder_name, len(files), dt_first, dt_last])

    start_date = min(extracted_dates) if extracted_dates else "Unknown"
    end_date = max(extracted_dates) if extracted_dates else "Unknown"

    image_files.sort()
    representative_image = image_files[0]
    meta = get_detailed_metadata(representative_image)

    # --- 1. Assemble and Save XML ---
    root = ET.Element("CatalogMetadata")
    
    project_summary = ET.SubElement(root, "CatalogSummary")
    ET.SubElement(project_summary, "TotalImages").text = str(len(image_files))
    ET.SubElement(project_summary, "StartDate").text = start_date
    ET.SubElement(project_summary, "EndDate").text = end_date
    ET.SubElement(project_summary, "RepresentativeFile").text = representative_image.name
    
    img_props = ET.SubElement(root, "UniversalImageProperties")
    for k, v in meta['Image'].items():
        ET.SubElement(img_props, k).text = v
        
    cam_props = ET.SubElement(root, "UniversalCameraProperties")
    for k, v in meta['Camera'].items():
        ET.SubElement(cam_props, k).text = v
        
    spatial_data = ET.SubElement(root, "SpatialAndOrientationData")
    ET.SubElement(spatial_data, "Latitude").text = "68.29964"
    ET.SubElement(spatial_data, "Longitude").text = "-30.74987"
    ET.SubElement(spatial_data, "Altitude").text = "88"
    ET.SubElement(spatial_data, "Yaw").text = "264"
    ET.SubElement(spatial_data, "Pitch").text = "2"
    ET.SubElement(spatial_data, "Roll").text = "0"
    
    user_notes = ET.SubElement(root, "UserNotes")
    ET.SubElement(user_notes, "Notes").text = "Left hand of the two cameras on the eastside. C06 from Erin's cameras."
    ET.SubElement(user_notes, "FieldOfView").text = "West side of terminus."
    
    xml_output_file = base_dir / (DIRECTORY_TO_SCAN[74:]+".xml")
    try:
        with open(xml_output_file, "w", encoding="utf-8") as f:
            f.write(prettify_xml(root))
        print(f"\nSuccess! Cataloged {len(image_files)} images based on {representative_image.name}.")
        print(f"Start Date: {start_date}")
        print(f"End Date:   {end_date}")
        print(f"Generated:  {xml_output_file.name}")
    except Exception as e:
        print(f"Failed to write XML: {e}")


    # --- 2. Assemble and Save CSV ---
    csv_output_file = base_dir / (DIRECTORY_TO_SCAN[74:]+ ".csv")
    try:
        csv_rows.sort(key=lambda x: x[0])
        
        with open(csv_output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Subfolder", "Image_Count", "Start_Time", "End_Time"])
            writer.writerows(csv_rows)
        print(f"Generated:  {csv_output_file.name}")
    except Exception as e:
        print(f"Failed to write CSV: {e}")


    # --- 3. Generate Temporal Coverage Plot ---
    try:
        plot_data = []
        for row in csv_rows:
            folder, count, start_str, end_str = row
            start_dt = parse_exif_date(start_str)
            end_dt = parse_exif_date(end_str)
            
            if start_dt and end_dt:
                plot_data.append({
                    'folder': folder,
                    'start': start_dt,
                    'end': end_dt,
                    'duration': end_dt - start_dt
                })
        
        if plot_data:
            # Sort chronologically by start date for a cleaner waterfall look
            plot_data.sort(key=lambda x: x['start'], reverse=True)
            
            folders = [item['folder'] for item in plot_data]
            start_dates = [item['start'] for item in plot_data]
            durations = [item['duration'] for item in plot_data]
            
            fig, ax = plt.subplots(figsize=(12, min(4 + len(folders) * 0.5, 12)))
            
            ax.barh(folders, durations, left=start_dates, color='steelblue', edgecolor='black')
            
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate() # Auto-rotates dates to prevent overlap
            
            plt.xlabel("Acquisition Date")
            plt.ylabel("Subfolder")
            plt.title("Camera Imagery Temporal Coverage & Gaps")
            plt.grid(axis='x', linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            plot_output_file = base_dir / (DIRECTORY_TO_SCAN[74:]+".png")
            plt.savefig(plot_output_file, dpi=150)
            print(f"Generated:  {plot_output_file.name}")
        else:
            print("No valid dates found to generate a plot.")
    except Exception as e:
        print(f"Failed to generate plot: {e}")

if __name__ == "__main__":
    DIRECTORY_TO_SCAN = r"L:\work\scientific_work_areas\land_instruments\RAW_DATA_BACKUP\TL CAMERAS\WEST_LOOKOUT_GOPRO_LEFT"
    
    process_directory(DIRECTORY_TO_SCAN)

    #%%