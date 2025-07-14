"""
Extract the "relevant" context from code
- What shoud be the input to this module?
- What is the definition of "relevant" context?
- Shoud we query some persistent data, e.g., vector database?

There are several possibles ways to use this module:    
1. Take the "bug trace" produced by RepoAudit, and collect more "relevant" context from the codebase, which will be used by the PathValidator.
2. Called by the DataflowAnalyzer of RepoAudit, so that the DataflowAnalyzer can better generate the summareis of the dataflow by utlizng the "relevant" context.
"""

