# javadoc2md: Javadoc to Markdown for AI Code Assistants

javadoc2md is a tool for converting Java [Javadoc](https://docs.oracle.com/javase/8/docs/technotes/tools/windows/javadoc.html) HTML documentation into clean, context-rich Markdown files. It is designed to provide high-quality, deduplicated documentation context for AI code assistants and LLM-based developer tools.

## Features
- Downloads the Javadoc JAR from [Maven Central](https://search.maven.org/) (by groupId, artifactId, and optional version)
- Extracts only class documentation (removes headers/footers/notes/links)
- Converts to Markdown, preserving package structure
- Creates a structured directory with the documentation files
- **Purpose-built for AI code assistants and LLMs**: output is optimized for ingestion as context

## Requirements
- Python 3.8+
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
- [markdownify](https://pypi.org/project/markdownify/)
- [tqdm](https://pypi.org/project/tqdm/)
- [requests](https://pypi.org/project/requests/)

## Installation

Clone the repository and synchronize dependencies:

```bash
git clone <repository-url>
cd javadoc2md
uv sync
```

## Usage

```bash
# Download and convert a specific version
javadoc2md --group com.google.guava --artifact guava --version 33.0.0-jre --output ./docs/

# Get the latest version
javadoc2md --group com.google.guava --artifact guava --output ./docs/
```

This will create a directory structure like:
```
./docs/guava-33.0.0-jre/
├── com/
│   └── google/
│       └── common/
│           ├── collect/
│           │   ├── ImmutableList.md
│           │   └── Lists.md
│           └── base/
│               ├── Optional.md
│               └── Strings.md
└── ...
```

## Intended Use
This tool is intended to generate context for AI code assistants, LLMs, and developer tools that require high-quality, deduplicated, and easily-parsable documentation.

## License
MIT