# RepoAudit

RepoAudit is a repo-level bug detector for general bugs. Currently it supports the detection of three types of bug: Null Pointer Dereference (NPD), Memory Leak (MLK), and Use After Free (UAF). It leverages [LLMSCAN](https://github.com/PurCL/LLMSCAN) to parse the codebase and use LLM to simulate the program's execution to analyze the data-flow facts starting with the designated source points.


## Features

- Compilation Free Analysis
- Multi-Linguistic Support
- Multiple Bug Type Detection
- Detailed Bug Reports
- Convenient WebUI Interface


## Installation

1. Clone the repository:

   ```sh
   git clone git@github.com:PurCL/RepoAudit.git --recursive
   cd RepoAudit
   ```

2. Install the required dependencies:

   ```sh
   pip install -r requirements.txt
   ```

3. Ensure you have the Tree-sitter library and language bindings installed:

   ```sh
   cd lib
   python build.py
   ```

4. Configure LLM API keys. For Claude3.5, we use the model hosted by Amazon Bedrock.

   ```sh
   export OPENAI_API_KEY=xxxxxx >> ~/.bashrc
   export DEEPSEEK_API_KEY=xxxxxx >> ~/.bashrc
   ```



## Quick Start

1. Prepare the project that you want to analyze and store them in directory `banchmark`. Here we've provided several projects in the directory `benchmark` for your quick-start.

2. Command Line: Run `run_repoaudit.sh`.

   ```sh
   > cd src
   
   # For NPE detection upon the directory `benchmark/Java/toy/NPD`.
   > sh run_repoaudit.sh
   ```


## Result
### Buggy Trace Report Format

**Key: Buggy trace**  
Each key represents a unique buggy trace propagation path, detailing how a bug propagates through function calls and code execution. The structure is as follows:

```
{
    Explanation: Detailed explanation of the propagation path.
    Path: Array of steps along the trace, where each step is an object with:
          {
              source:      The source code fragment or operation (e.g., "return NULL;"),
              src_line:    The corresponding line number in the source file,
              function_name: The name of the function where the step occurs,
              function_code: The full code of the function (providing context),
              file_name:   The file path where the function is located
          }
    Vali_LLM:    The validation result produced by the LLM (e.g., "True" or "False"),
    Vali_human:  The human validation result (typically empty until reviewed)
}
```

### WebUI

You can also use our webUI to quickly check the detection results.

   ```sh
   cd src/webUI
   streamlit run home.py
   ```

## More

For more information, 
please refer this paper: [RepoAudit: An Autonomous LLM-Agent for Repository-Level Code Auditing](https://arxiv.org/pdf/2501.18160v2).
The detailed documentation will be ready very soon.

## License

This project is licensed under the **GNU General Public License v2.0 (GPLv2)**.  You are free to use, modify, and distribute the software under the terms of this license, provided that derivative works are also distributed under the same license.

For full details, see the [LICENSE](LICENSE) file or visit the official license page: [https://www.gnu.org/licenses/old-licenses/gpl-2.0.html](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)

