"""
Starter scaffold for the CS 294-264 HW1 ReAct agent.

Students must implement a minimal ReAct agent that:
- Maintains a message history list (role, content, timestamp, unique_id)
- Uses a textual function-call format (see ResponseParser) with rfind-based parsing
- Alternates Reasoning and Acting until calling the tool `finish`
- Supports tools: `run_bash_cmd`, `finish`

This file intentionally omits core implementations and replaces them with
clear specifications and TODOs.
"""

from typing import List, Callable, Dict, Any
import time

from response_parser import ResponseParser
from llm import LLM, OpenAIModel
import inspect

class ReactAgent:
    """
    Minimal ReAct agent that:
    - Maintains a message history list with unique ids
    - Builds the LLM context from the message list
    - Registers callable tools with auto-generated docstrings in the system prompt
    - Runs a Reason-Act loop until `finish` is called or MAX_STEPS is reached
    """

    def __init__(self, name: str, parser: ResponseParser, llm: LLM):
        self.name: str = name
        self.parser = parser
        self.llm = llm

        # Message list storage
        self.id_to_message: List[Dict[str, Any]] = []
        self.root_message_id: int = -1
        self.current_message_id: int = -1

        # Registered tools
        self.function_map: Dict[str, Callable] = {}

        # Set up the initial structure of the history
        # Create required root nodes and a user node (task)
        system_prompt = """You are an expert software engineer who fixes bugs quickly and efficiently.

⚠️ CRITICAL: You MUST use replace_in_file to make actual code changes. Calling finish() without making changes is FAILURE.

=== CORE PRINCIPLE ===
MAKE CHANGES FAST. Keep solutions SIMPLE. Search thoroughly to find the right code, but don't overthink the solution once you find it. It's better to try a simple fix than to create complex solutions.

=== WORKFLOW (Complete in <20 steps) ===

1. UNDERSTAND (1-2 steps)
   - Read the issue - what's broken?
   - Extract: class/function names, error messages, file hints

2. LOCATE (2-5 steps)
   - search_in_files for the main class/function mentioned
   - If no results, try alternative searches
   - Use find_file if you know the filename
   - After 4-5 attempts, pick the most likely file and proceed

3. EXAMINE (1-2 steps)
   - show_file on the most relevant file - read it COMPLETELY
   - If tests exist, show_file on test file to understand expected behavior

4. ANALYZE ROOT CAUSE (1 step) - MANDATORY!
   - Explain WHY the bug exists (not just what's broken)
   - Keep it simple - don't overthink
   - Example: "Bug exists because inspect.isfunction() returns False for properties"

5. FIX (1-2 steps)
   - Use replace_in_file IMMEDIATELY once you understand root cause
   - Copy EXACT text from show_file (every space, tab, newline)
   - Make MINIMAL, SIMPLE change addressing ROOT CAUSE
   - If replacement fails, re-read and try ONCE more

6. VERIFY (2-3 steps) - MANDATORY!
   - run_bash_cmd to test (e.g., python -m pytest path/to/test.py -xvs)
   - Try multiple test commands if first fails: python -m pytest, python3 -m pytest, ./runtests.py
   - If tests pass → finish
   - If tests fail → analyze failure and fix ONCE more

7. FINISH
   - Call finish with brief summary of your fix
   - Ensure result string is clean (no function markers!)

=== KEY PRINCIPLES ===

1. EXPLAIN WHY: "Bug exists because X returns False for Y" (not just "need to handle Y")

2. KEEP IT SIMPLE: Don't create complex solutions. Simple fixes are better.

3. MODIFY EXISTING CODE: Don't create new files when you can modify existing code.

4. EXACT TEXT: Copy EXACT text from show_file (every space, tab, newline).

=== TOOLS (Use sparingly!) ===

search_in_files(pattern, file_pattern="*") - Find code
  search_in_files("class User") → finds class definition
  search_in_files("test_user", "*.py") → finds test files
  Use as many searches as needed to find the right code

show_file(file_path) - Read complete file
  show_file("src/user.py") → read entire file with line numbers
  show_file("tests/test_user.py") → read tests to understand expected behavior
  Always read COMPLETE files, not snippets

replace_in_file(file_path, old_str, new_str) - Fix the bug!
  CRITICAL: Copy EXACT text from show_file (every space, tab, newline)
  If it fails: re-read file, copy exact text, try once more
  NEVER include function markers like "----END_FUNCTION_CALL" in code!

run_bash_cmd(command) - Run tests
  run_bash_cmd("python -m pytest tests/test_user.py -xvs") → run specific test
  run_bash_cmd("python3 -m pytest tests/test_user.py::test_edge_case -xvs") → run one test
  Try multiple commands if first fails: python -m pytest, python3 -m pytest, ./runtests.py
  Use to verify your fix works AND test edge cases
  NEVER skip testing just because "pytest: command not found"!

find_file(filename) - Locate files
  find_file("user.py") → find file paths
  find_file("test_*.py") → find test files

list_directory(path) - Explore structure
  list_directory(".") → see project layout
  list_directory("tests") → see test structure

=== CRITICAL RULES ===

1. UNDERSTAND ROOT CAUSE - Explain WHY before fixing WHAT. Don't fix symptoms!

2. MODIFY EXISTING CODE - Don't create new files when existing code can be fixed.

3. FIX AT RIGHT LEVEL - Distinguish data generation vs. formatting, rendering vs. prep.

4. TEST EDGE CASES - MANDATORY! Test null, both branches, with/without optional params. Try multiple test commands.

5. CHECK REGRESSIONS - MANDATORY! Run ALL related tests to ensure existing tests still pass. Don't break working code!

6. TEST OPPOSITE CASE - If fixing blank=False, test blank=True. If fixing with-password, test without-password.

5. EXACT TEXT MATCHING - Copy EXACT text from show_file (every space/tab/newline).

6. CLEAN OUTPUT - Never include function markers in code or finish result.

7. READ TESTS FIRST - If tests exist, read them to understand expected behavior.
   - **Pay attention to test names!** They tell you what's being tested.
   - Example: Test named "test_modelchoicefield_radio" → Fix ModelChoiceField, not ForeignKey!
   - Look for ALL related tests, not just the one mentioned in the issue.

8. ACTUALLY MAKE CHANGES - You MUST call replace_in_file. Don't just analyze!

=== COMMON MISTAKES ===

❌ Creating complex solutions → Keep it SIMPLE
❌ Creating new files → Modify existing code
❌ Fixing symptoms → Explain WHY bug exists
❌ Not copying exact text → Copy EXACT text from show_file (whitespace matters!)
❌ Searching 10+ times without finding anything → Use find_file or list_directory
❌ Not testing → Try python -m pytest, python3 -m pytest, ./runtests.py
❌ Calling finish without changes → You MUST use replace_in_file!

=== EXAMPLE ===

Issue: "InheritDocstrings metaclass doesn't work for properties"

1. search_in_files("InheritDocstrings") → Found: ./astropy/utils/misc.py:497
2. show_file("astropy/utils/misc.py") → See InheritDocstrings class, uses inspect.isfunction
3. ANALYZE: "Root cause: inspect.isfunction() returns False for properties, so line 522 skips them"
4. replace_in_file("astropy/utils/misc.py",
     "            if (inspect.isfunction(val) and",
     "            if ((inspect.isfunction(val) or isinstance(val, property)) and")
5. run_bash_cmd("pytest astropy/utils/tests/test_misc.py::test_inherit_docstrings -xvs") → Tests pass!
6. finish("Fixed InheritDocstrings to handle properties by adding isinstance(val, property) check")

=== YOUR GOAL ===
Fix the bug in <20 steps. Keep it SIMPLE. Understand root cause, make minimal fix, test, finish.

⚠️ REMEMBER: Simple solutions are better than complex ones!
"""
        self.system_message_id = self.add_message("system", system_prompt)
        self.user_message_id = self.add_message("user", "")
        # NOTE: mandatory finish function that terminates the agent
        self.add_functions([self.finish])

    # -------------------- MESSAGE LIST --------------------
    def add_message(self, role: str, content: str) -> int:
        """
        Create a new message and add it to the list.

        The message must include fields: role, content, timestamp, unique_id.
        """
        # Use list index as unique_id for O(1) access
        unique_id = len(self.id_to_message)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "unique_id": unique_id
        }
        
        self.id_to_message.append(message)
        return unique_id

    def set_message_content(self, message_id: int, content: str) -> None:
        """
        Update message content by id.
        """
        self.id_to_message[message_id]["content"] = content

    def get_context(self) -> str:
        """
        Build the full LLM context from the message list.
        """
        context_parts = []
        for message in self.id_to_message:
            context_parts.append(self.message_id_to_context(message["unique_id"]))
        return "".join(context_parts)

    # -------------------- REQUIRED TOOLS --------------------
    def add_functions(self, tools: List[Callable]):
        """
        Add callable tools to the agent's function map.

        The system prompt must include tool descriptions that cover:
        - The signature of each tool
        - The docstring of each tool
        """
        for tool in tools:
            # Use function.__name__ as the key in the function map
            self.function_map[tool.__name__] = tool
    
    def finish(self, result: str):
        """The agent must call this function with the final result when it has solved the given task. The function calls "git add -A and git diff --cached" to generate a patch and returns the patch as submission.

        Args: 
            result (str); the result generated by the agent

        Returns:
            The result passed as an argument.  The result is then returned by the agent's run method.
        """
        return result 

    # -------------------- MAIN LOOP --------------------
    def run(self, task: str, max_steps: int) -> str:
        """
        Run the agent's main ReAct loop:
        - Set the user prompt
        - Loop up to max_steps (<= 100):
            - Build context from the message list (with `message_id_to_context`)
            - Query the LLM
            - Parse a single function call at the end (see ResponseParser)
            - Execute the tool
            - Append tool result to the list
            - If `finish` is called, return the final result
        """
        # Set the user task message
        self.set_message_content(self.user_message_id, task)
        
        # Enforce max_steps cap at 100
        max_steps = min(max_steps, 100)
        
        # Main ReAct loop
        for step in range(max_steps):
            # Build context from message history
            context = self.get_context()
            
            # Convert message history to OpenAI API format
            messages = []
            for msg in self.id_to_message:
                role = msg["role"]
                # Map "tool" role to "user" for OpenAI API compatibility
                if role == "tool":
                    role = "user"
                
                messages.append({
                    "role": role,
                    "content": self.message_id_to_context(msg["unique_id"])
                })
            
            # Query the LLM
            try:
                response = self.llm.generate(messages)
            except Exception as e:
                # LLM API failure - add error and continue
                error_msg = f"LLM API error: {str(e)}"
                self.add_message("tool", error_msg)
                continue
            
            # Add the LLM response as an assistant message
            self.add_message("assistant", response)
            
            # Parse the response to extract function call
            try:
                parsed = self.parser.parse(response)
            except ValueError as e:
                # Parse error - add error message and continue
                error_msg = f"Parse error: {str(e)}"
                self.add_message("tool", error_msg)
                continue
            
            # Look up the function in the function map
            func_name = parsed["name"]
            if func_name not in self.function_map:
                # Unknown function - add error message and continue
                error_msg = f"Unknown function: {func_name}"
                self.add_message("tool", error_msg)
                continue
            
            # Execute the function with parsed arguments
            func = self.function_map[func_name]
            try:
                result = func(**parsed["arguments"])
                
                # Check if finish was called
                if func_name == "finish":
                    return result
                
                # Add the function result as a tool message
                self.add_message("tool", str(result))
                
            except Exception as e:
                # Function execution error - add error message and continue
                error_msg = f"Function execution error: {str(e)}"
                self.add_message("tool", error_msg)
                continue
        
        # Max steps reached without calling finish
        return ""

    def message_id_to_context(self, message_id: int) -> str:
        """
        Helper function to convert a message id to a context string.
        """
        message = self.id_to_message[message_id]
        header = f'----------------------------\n|MESSAGE(role="{message["role"]}", id={message["unique_id"]})|\n'
        content = message["content"]
        if message["role"] == "system":
            tool_descriptions = []
            for tool in self.function_map.values():
                signature = inspect.signature(tool)
                docstring = inspect.getdoc(tool)
                tool_description = f"Function: {tool.__name__}{signature}\n{docstring}\n"
                tool_descriptions.append(tool_description)

            tool_descriptions = "\n".join(tool_descriptions)
            return (
                f"{header}{content}\n"
                f"--- AVAILABLE TOOLS ---\n{tool_descriptions}\n\n"
                f"--- RESPONSE FORMAT ---\n{self.parser.response_format}\n"
            )
        else:
            return f"{header}{content}\n"

def main():
    from envs import DumbEnvironment
    llm = OpenAIModel("----END_FUNCTION_CALL----", "gpt-4o-mini")
    parser = ResponseParser()

    env = DumbEnvironment()
    dumb_agent = ReactAgent("dumb-agent", parser, llm)
    dumb_agent.add_functions([env.run_bash_cmd])
    result = dumb_agent.run("Show the contents of all files in the current directory.", max_steps=10)
    print(result)

if __name__ == "__main__":
    # Optional: students can add their own quick manual test here.
    main()
