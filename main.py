"""
jdoc2md: Java Javadoc HTML to Markdown Converter

This tool downloads a Java library's Javadoc JAR from Maven Central (by groupId, artifactId, and optional version), extracts the HTML, converts each class page to Markdown (removing redundant content), and creates a directory structure with the documentation.

Usage (as CLI):
    jdoc2md --group com.google.guava --artifact guava --version 33.0.0-jre --output guava-docs/
    # or to get the latest version:
    jdoc2md --group com.google.guava --artifact guava --output guava-docs/

Features:
- Downloads the javadoc JAR from Maven Central
- Extracts only class documentation (removes headers/footers/notes/links)
- Converts to Markdown, preserving package structure
- Creates a directory structure with the documentation

Requirements:
- Python 3.8+
- beautifulsoup4, markdownify, tqdm, requests

"""
import sys
import os
import shutil
import zipfile
import subprocess
from pathlib import Path
from tqdm import tqdm
from bs4 import BeautifulSoup
import markdownify
import requests
import tempfile
import argparse
import re

def extract_jar(jar_path, extract_to):
    with zipfile.ZipFile(jar_path, 'r') as jar:
        jar.extractall(extract_to)

def convert_html_to_md(html_path, md_path):
    # Use markitdown CLI to convert HTML to Markdown
    subprocess.run([
        sys.executable, '-m', 'markitdown', html_path, '-o', md_path
    ], check=True)

def extract_class_sections(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    main = soup.find('main')
    if not main:
        return ""
    # Only include elements with allowed classes, exclude unwanted classes
    allowed = {"header", "inheritance", "class-description", "summary", "details-list"}
    exclude = {"notes", "inherited-list"}
    sections = []
    for el in main.find_all(recursive=False):
        classes = set(el.get('class', []))
        if classes & allowed and not classes & exclude:
            # Remove all sub-elements with excluded classes
            for bad in el.find_all(class_=lambda c: c and any(x in c for x in exclude)):
                bad.decompose()
            # Remove all anchor tags but keep their text
            for a in el.find_all('a'):
                a.replace_with(a.get_text())
            sections.append(str(el))
    # Convert to markdown
    md = markdownify.markdownify("\n\n".join(sections), heading_style="ATX")
    return md

def process_class_html(html_path, md_path):
    md_content = extract_class_sections(html_path)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

def download_javadoc_jar(group, artifact, version=None):
    """Download the javadoc jar from Maven Central. Returns the path to the downloaded file."""
    base_url = "https://repo1.maven.org/maven2"
    group_path = group.replace('.', '/')
    if version is None:
        # Find latest version
        metadata_url = f"{base_url}/{group_path}/{artifact}/maven-metadata.xml"
        resp = requests.get(metadata_url)
        if resp.status_code != 200:
            raise Exception(f"Could not fetch metadata for {group}:{artifact}")
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)
        version = root.findtext("versioning/latest") or root.findtext("versioning/release")
        if not version:
            raise Exception("Could not determine latest version from maven-metadata.xml")
    jar_url = f"{base_url}/{group_path}/{artifact}/{version}/{artifact}-{version}-javadoc.jar"
    resp = requests.get(jar_url, stream=True)
    if resp.status_code != 200:
        raise Exception(f"Could not download javadoc jar: {jar_url}")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jar")
    for chunk in resp.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()
    return tmp.name, version

def slugify(value):
    value = str(value).strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = re.sub(r'-+', '-', value)
    return value.strip('-')

def main():
    parser = argparse.ArgumentParser(description="Convert Java Javadoc HTML to Markdown directory structure.")
    parser.add_argument('--group', help='Maven groupId')
    parser.add_argument('--artifact', help='Maven artifactId')
    parser.add_argument('--version', help='Maven version (optional, latest if omitted)')
    parser.add_argument('-o', '--output', required=True, help='Output directory path')
    parser.add_argument('-i', '--input-jar', help='Path to local javadoc jar file (if provided, skips download)')
    args = parser.parse_args()

    if args.input_jar:
        jar_file = args.input_jar
        version = None
        artifact = args.artifact or "unknown"
        print(f"Using local jar: {jar_file}")
    elif args.artifact and not args.group:
        print(f"ArtifactId '{args.artifact}' provided without groupId.")
        print("Searching for available groupIds and versions on Maven Central...")
        # Query Maven Central for groupIds and versions for this artifact
        search_url = f"https://search.maven.org/solrsearch/select?q=a:{args.artifact}&rows=100&wt=json"
        resp = requests.get(search_url)
        if resp.status_code != 200:
            print("Error querying Maven Central.")
            return
        docs = resp.json().get('response', {}).get('docs', [])
        if not docs:
            print("No results found for artifactId.")
            return
        # Group by groupId and collect all versions
        from collections import defaultdict
        group_versions = defaultdict(set)
        for doc in docs:
            group = doc.get('g')
            version = doc.get('v')
            if group and version:
                group_versions[group].add(version)
        if not group_versions:
            print("No groupIds with versions found for this artifactId.")
            return
        print("Select a groupId:")
        group_list = list(group_versions.keys())
        for idx, group in enumerate(group_list):
            print(f"  {idx+1}. {group}")
        sel = input("Enter number: ")
        try:
            sel_idx = int(sel) - 1
            if sel_idx < 0 or sel_idx >= len(group_list):
                print("Invalid selection.")
                return
        except Exception:
            print("Invalid input.")
            return
        group = group_list[sel_idx]
        versions = sorted(group_versions[group], reverse=True)[:10]
        print(f"Available versions for {group}:{args.artifact} (latest 10):")
        for idx, v in enumerate(versions):
            print(f"  {idx+1}. {v}")
        vsel = input("Select version number: ")
        try:
            vsel_idx = int(vsel) - 1
            if vsel_idx < 0 or vsel_idx >= len(versions):
                print("Invalid selection.")
                return
        except Exception:
            print("Invalid input.")
            return
        version = versions[vsel_idx]
        print(f"Selected: {group}:{args.artifact}:{version}")
        jar_file, _ = download_javadoc_jar(group, args.artifact, version)
        artifact = args.artifact
    else:
        if not args.group or not args.artifact:
            parser.error('Either --input-jar or both --group and --artifact must be provided.')
        print(f"Downloading javadoc jar for {args.group}:{args.artifact}:{args.version or 'latest'}...")
        jar_file, version = download_javadoc_jar(args.group, args.artifact, args.version)
        print(f"Downloaded version: {version}")
        artifact = args.artifact

    # Prepare temp dir for extraction
    temp_extract_dir = Path(tempfile.mkdtemp(prefix="jdoc2md_extract_"))
    
    # Create output directory name: {artifact}-{version}
    version_str = version or 'latest'
    output_dir_name = f"{artifact}-{version_str}"
    final_output_dir = Path(args.output) / output_dir_name
    
    try:
        extract_jar(jar_file, temp_extract_dir)
        # Only process class HTML files (skip index, overview, etc.)
        html_files = []
        for root, _, files in os.walk(temp_extract_dir):
            for file in files:
                if file.lower().endswith('.html') and not any(
                    file.startswith(prefix) for prefix in [
                        'index', 'overview', 'allclasses', 'allpackages', 'constant-values', 'deprecated-list', 'help', 'search', 'serialized-form']):
                    html_path = os.path.join(root, file)
                    rel_path = os.path.relpath(html_path, temp_extract_dir)
                    md_path = final_output_dir / (os.path.splitext(rel_path)[0] + '.md')
                    html_files.append((html_path, md_path))
        
        # Create final output directory
        final_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Show progress bar while converting
        for html_path, md_path in tqdm(html_files, desc="Converting class HTML to Markdown", unit="file"):
            process_class_html(html_path, md_path)
        
        print(f"Created Markdown documentation directory: {final_output_dir}")
        print(f"Total files converted: {len(html_files)}")
        
    finally:
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        if not args.input_jar and os.path.exists(jar_file):
            os.remove(jar_file)

if __name__ == "__main__":
    main()