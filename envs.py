from utils import get_sb_environment
import subprocess
import swebench

class LimitsExceeded(Exception):
    """Raised when the agent has reached its step limit."""


class SWEEnvironment:
    """
    Minimal interface to the SWEBench execution environment.

    Students may use their own wrapper. The environment must expose:
    - execute(command: str) -> str: Run a shell command and return stdout, or raise ValueError on failure
    """

    def __init__(self, instance: dict):
        self.env = get_sb_environment(instance)
        self.instance = instance  # Store instance for test execution
     
    # -------------------- REQUIRED TOOLS --------------------
    def run_bash_cmd(self, command: str) -> str:
        """
        Run the command in a bash shell and return the output or throw a ValueError
        if the process returns non-zero exit code.

        Args;
            command (str): the shell command to run

        Returns:
            The output of running the shell command
        """
        try:
            output = self.env.execute(command)
            
            # Handle case where execute returns a dict instead of string
            if isinstance(output, dict):
                output = output.get("output", "") or output.get("stdout", "")
                
        except subprocess.TimeoutExpired as e:
            output = e.output.decode("utf-8", errors="replace") if e.output else ""
            raise ValueError(output)
        except TimeoutError:
            raise ValueError("TimeoutError")
        return output
    
    def generate_patch(self, result: str) -> str:
        """
        Generate a patch from the result (for SWE-Bench)
        """
        try:
            patch_output = self.env.execute("git add -A && git diff --cached")
            
            # Handle case where execute returns a dict instead of string
            if isinstance(patch_output, dict):
                patch_output = patch_output.get("output", "") or patch_output.get("stdout", "")
            
            if patch_output and patch_output.strip():
                return patch_output
            else:
                return f"{result}\n\nNo changes detected to generate a patch."
        except Exception as e:
            return f"{result}\n\nError running git commands: {e}"

    # -------------------- TODO(student): add more functions here if you want, not required --------------------
    def replace_in_file(self, file_path: str, old_str: str, new_str: str) -> str:
        """
        Replace old_str with new_str in the specified file.
        Uses Python to avoid shell escaping issues.
        
        Args:
            file_path (str): Path to the file to modify
            old_str (str): The exact string to find and replace
            new_str (str): The string to replace it with
            
        Returns:
            Success message or error description
        """
        try:
            # Use Python heredoc to avoid all shell escaping issues
            python_cmd = f'''python3 << 'EOFMARKER'
with open("{file_path}", "r") as f:
    content = f.read()

old_str = {repr(old_str)}
new_str = {repr(new_str)}

if old_str not in content:
    print("ERROR: Could not find the specified text in file")
    exit(1)

new_content = content.replace(old_str, new_str, 1)

with open("{file_path}", "w") as f:
    f.write(new_content)

print("Successfully replaced text in {file_path}")
EOFMARKER
'''
            result = self.run_bash_cmd(python_cmd)
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    def show_file(self, file_path: str, start_line: int = 1, end_line: int = None) -> str:
        """
        Show the content of a file with line numbers.
        
        Args:
            file_path (str): Path to the file to show
            start_line (int): Starting line number (1-indexed, default 1)
            end_line (int, optional): Ending line number (1-indexed)
            
        Returns:
            The file content with line numbers
        """
        try:
            # First check if file exists
            self.run_bash_cmd(f"test -f {file_path}")
            
            if end_line is not None:
                # Show specific line range with line numbers
                cmd = f"sed -n '{start_line},{end_line}p' {file_path} | nl -v {start_line}"
            else:
                # Show from start_line to end with line numbers
                cmd = f"tail -n +{start_line} {file_path} | nl -v {start_line}"
            
            return self.run_bash_cmd(cmd)
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"
    
    def find_file(self, filename: str) -> str:
        """
        Find a file by name in the repository.
        
        Args:
            filename (str): Name of the file to find
            
        Returns:
            Paths to matching files
        """
        try:
            cmd = f"find . -name '{filename}' -type f 2>/dev/null | head -20"
            return self.run_bash_cmd(cmd)
        except Exception as e:
            return f"Error finding file: {str(e)}"
    
    def search_in_files(self, pattern: str, file_pattern: str = "*") -> str:
        """
        Search for a pattern in files.
        
        Args:
            pattern (str): Pattern to search for
            file_pattern (str): File pattern to search in (default: *)
            
        Returns:
            Lines containing the pattern with file names and line numbers
        """
        try:
            cmd = f"grep -rn '{pattern}' --include='{file_pattern}' . 2>/dev/null | head -50"
            return self.run_bash_cmd(cmd)
        except Exception as e:
            return f"Error searching: {str(e)}"
    
    def list_directory(self, path: str = ".") -> str:
        """
        List contents of a directory.
        
        Args:
            path (str): Directory path (default: current directory)
            
        Returns:
            Directory listing
        """
        try:
            cmd = f"ls -la {path}"
            return self.run_bash_cmd(cmd)
        except Exception as e:
            return f"Error listing directory: {str(e)}"

class DumbEnvironment:
    """
    Dumb environment that just executes the command
    """

    def execute(self, command: str) -> str:
        """
        Run the command in bash and return the output

        Args;
            command (str): the shell command to run

        Returns:
            The output of running the shell command
        """
        result = subprocess.run(command, capture_output=True, shell=True, check=False)
        output = f"--STDOUT--\n{result.stdout.decode()}\n--STDERR--\n{result.stderr.decode()}"
        if result.returncode:
            raise ValueError(output)
        return output
    
    def run_bash_cmd(self, command: str) -> str:
        """
        Run the command in a bash shell and return the output or throw a ValueError
        if the process returns non-zero exit code.

        Args;
            command (str): the shell command to run

        Returns:
            The output of running the shell command
        """
        return self.execute(command)
