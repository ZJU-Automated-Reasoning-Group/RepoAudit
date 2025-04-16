# RepoAudit

RepoAudit is a repo-level bug detector for general bugs. Currently, it supports the detection of diverse bug types (such as Null Pointer Dereference, Memory Leak, and Use After Free) in multiple programming languages (including C/C++, Java, Python, and Go). It leverages [LLMSCAN](https://github.com/PurCL/LLMSCAN) to parse the codebase and uses LLM to mimic the process of manual code auditing. Compared with existing code auditing tools, RepoAudit offers the following advantages:

- Compilation-Free Analysis
- Multi-Lingual Support
- Multiple Bug Type Detection
- Customization Support

## Agents in RepoAudit

RepoAudit is a multi-agent framework for code auditing. We offer two agent instances in our current version:

- **MetaScanAgent** in `metascan.py`: Scan the project using tree-sitter–powered parsing-based analyzers and obtains the basic syntactic properties of the program.

- **DFBScanAgent** in `dfbscan.py`: Perform inter-procedural data-flow analysis as described in this [preprint](https://arxiv.org/abs/2501.18160). It detects data-flow bugs, including source-must-not-reach-sink bugs (e.g., Null Pointer Dereference) and source-must-reach-sink bugs (e.g., Memory Leak).

We are keeping implementing more agents and will open-source them very soon. Utilizing DFBScanAgent and other agents, we have discovered hundred of confirmed and fixed bugs in open-source community. You can refer to this [bug list](https://repoaudit-home.github.io/bugreports.html).

## Project Structure

The project structure is as follows:

```
# In src directory
├── agent                # Directory containing different agents for different uses
|   ├── agent.py         # The base class of agent
│   └── dfbscan.py       # The agent for data-flow bug detection.
├── llmtool              # Directory for LLM-based analyzers
│   ├── LLM_tool.py      # The base class of LLM-based analyzers as tools
│   ├── LLM_utils.py     # Utility class that invokes different LLMs
│   └──dfbscan          # LLM tools used in dfbscan
│       ├── intra_dataflow_analyzer.py  # LLM tool: Collect intra-procedural data-flow facts
│       └── path_validator.py   # LLM tool: Validate the path reachability
├── memory
│   ├── report           # Bug report 
│   │   └── bug_report.py
│   ├── semantic         # Semantic properties focused in different agents
│   │   ├── dfb_state.py
│   │   ├── metascan_state.py
│   │   └── state.py
│   └── syntactic        # Syntactic properties, i.e., AST info
│       ├── api.py
│       ├── function.py
│       └── value.py
├── tstool
│   ├── analyzer         # parsing-based analyzer
│   │   ├── Cpp_TS_analyzer.py      # C/C++ analyzer
│   │   ├── Go_TS_analyzer.py       # Go analyzer
│   │   ├── Java_TS_analyzer.py     # Java analyzer
│   │   ├── Python_TS_analyzer.py   # Python analyzer
│   │   ├── TS_analyzer.py          # Base class
│   └── dfbscan_extractor # Extractors used in dfbscan (based on parsing)
│       ├── Cpp
│       │   ├── Cpp_MLK_extractor.py
│       │   ├── Cpp_NPD_extractor.py
│       │   ├── Cpp_UAF_extractor.py
│       ├── Java
│       │   └── Java_NPD_extractor.py
│       └── dfbscan_extractor.py
├── prompt # Prompt templates
│   ├── Cpp
│   │   └── dfbscan    # Prompts used in dfbscan for Cpp program analysis
│   │       ├── intra_dataflow_analyzer.json
│   │       └── path_validator.json
│   ├── Go
│       └── dfbscan    # Prompts used in dfbscan for Python program analysis
│   ├── Java
│   │   └── dfbscan    # Prompts used in dfbscan for Java program analysis
│   │       ├── intra_dataflow_analyzer.json
│   │       └── path_validator.json
│   └── Python
│       └── dfbscan    # Prompts used in dfbscan for Python program analysis
├── ui                   # UI classes
│   └── logger.py        # Logger class
├── repoaudit.py         # Main entry of RepoAudit
└── run_repoaudit.sh     # Script for analyzing one project
```

## Installation

1. Install the required dependencies:

   ```sh
   cd RepoAudit
   pip install -r requirements.txt
   ```

2. Ensure you have the Tree-sitter library and language bindings installed:

   ```sh
   cd lib
   python build.py
   ```

3. Configure the OpenAI API key. 

   ```sh
   export OPENAI_API_KEY=xxxxxx >> ~/.bashrc
   ```

   For Claude3.5, we use the model hosted by Amazon Bedrock. If you want to use Claude-3.5 and Claude-3.7, you may need to set up the environment first.


## Quick Start

1. We have offered several toy programs as benchmarks for yor to have a quick start. You can just execute the script `src/run_repoaudit.sh` to scan files in the `benchmark/Java/toy/NPD` directory.

   ```sh
   cd RepoAudit/src
   sh run_repoaudit.sh dfbscan # Use the agent DFBScan
   ```

2. After the scanning is complete, you can check the resulting JSON and log files.

3. If you want to scan several real-world programs, you can choose your own projects or use directly execute the following command to fetch several projects for scanning:

   ```sh
   cd RepoAudit
   git submodule update --init --recursive
   ```

   The projects will be downloaded to the directory `benchmark`.


## Parallel Auditing Support

For some programs, a sequential analysis process may be quite time-consuming. To accelerate the analysis, you can choose parallel auditing. Specifically, you can set the option `--max-neural-workers` to a larger value. By default, this option is set to 6 for parallel auditing.

## More

We currently open-source the implementation of DFBSCanAgent for bug scanning. We will release more technical reports/research papers and open-source other agents in RepoAudit very soon. For more information, please refer to our website: [RepoAudit: Auditing Code As Human](https://repoaudit-home.github.io/).


## License

This project is licensed under the **GNU General Public License v2.0 (GPLv2)**.  You are free to use, modify, and distribute the software under the terms of this license, provided that derivative works are also distributed under the same license.

For full details, see the [LICENSE](LICENSE) file or visit the official license page: [https://www.gnu.org/licenses/old-licenses/gpl-2.0.html](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)