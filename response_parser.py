class ResponseParser:
    """
    Parses LLM responses to extract a single function call using a rigid textual format.

    The LLM must output exactly one function call at the end of its response.
    Do NOT use JSON or XML. Use rfind to locate the final markers.
    """

    BEGIN_CALL = "----BEGIN_FUNCTION_CALL----"
    END_CALL = "----END_FUNCTION_CALL----"
    ARG_SEP = "----ARG----"
    VALUE_SEP = "----VALUE----"

    # Students should include this exact template in the system prompt so the LLM follows it.
    response_format = f"""
your_thoughts_here
...
{BEGIN_CALL}
function_name
{ARG_SEP}
arg1_name
{VALUE_SEP}
arg1_value (can be multiline)
{ARG_SEP}
arg2_name
{VALUE_SEP}
arg2_value (can be multiline)
...
{END_CALL}

DO NOT CHANGE ANY TEST! AS THEY WILL BE USED FOR EVALUATION.
"""

    def parse(self, text: str) -> dict:
        """
        Parse the function call from `text` using string.rfind to avoid confusion with
        earlier delimiter-like content in the reasoning.

        Returns a dictionary: {"thought": str, "name": str, "arguments": dict}
        """
        # Use rfind to locate the last occurrence of markers
        begin_idx = text.rfind(self.BEGIN_CALL)
        end_idx = text.rfind(self.END_CALL)
        
        # Validate markers are present
        if begin_idx == -1:
            raise ValueError("Could not find BEGIN_FUNCTION_CALL marker in response")
        if end_idx == -1:
            raise ValueError("Could not find END_FUNCTION_CALL marker in response")
        
        # Extract thought (everything before BEGIN_CALL)
        thought = text[:begin_idx].strip()
        
        # Extract function call block (between BEGIN_CALL and END_CALL)
        call_block = text[begin_idx + len(self.BEGIN_CALL):end_idx]
        
        # Split the call block into lines
        lines = call_block.split('\n')
        
        # Extract function name (first non-empty line after BEGIN_CALL)
        function_name = None
        for line in lines:
            stripped = line.strip()
            if stripped:
                function_name = stripped
                break
        
        if not function_name:
            raise ValueError("Function name cannot be empty")
        
        # Parse arguments
        arguments = {}
        
        # Split on ARG_SEP to find argument sections
        arg_sections = call_block.split(self.ARG_SEP)
        
        # Skip the first section (contains function name)
        for section in arg_sections[1:]:
            # Each section should have format:
            # arg_name
            # ----VALUE----
            # arg_value
            
            if self.VALUE_SEP not in section:
                raise ValueError("Invalid argument format: expected ARG_SEP followed by VALUE_SEP")
            
            # Split on VALUE_SEP
            parts = section.split(self.VALUE_SEP, 1)
            
            if len(parts) != 2:
                raise ValueError("Invalid argument format: expected ARG_SEP followed by VALUE_SEP")
            
            # Extract argument name (first non-empty line before VALUE_SEP)
            arg_name = None
            for line in parts[0].split('\n'):
                stripped = line.strip()
                if stripped:
                    arg_name = stripped
                    break
            
            if not arg_name:
                raise ValueError("Invalid argument format: expected ARG_SEP followed by VALUE_SEP")
            
            # Extract argument value (everything after VALUE_SEP, preserving newlines)
            # Remove leading newline if present, but preserve internal newlines
            arg_value = parts[1]
            if arg_value.startswith('\n'):
                arg_value = arg_value[1:]
            # Remove trailing whitespace/newlines
            arg_value = arg_value.rstrip()
            
            arguments[arg_name] = arg_value
        
        return {
            "thought": thought,
            "name": function_name,
            "arguments": arguments
        }
