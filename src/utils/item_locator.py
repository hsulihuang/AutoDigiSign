#item_locator.py
import os

"""
    Function:
        find_item(): Find the first occurrence of a file or folder.
        find_all_items(): Find all occurrences of a file or folder.

    Parameters:
        name (str): The name of the file or folder to search for.
        search_directory (str): The directory to start the search from. Default is the current directory.
        skip_dirs (list): List of directories to skip during the search. Default is None.
        search_for (str): Specify 'file' to search for files, 'folder' to search for folders, or None to search for both. Default is None.

    Returns:
        find_item(): str: The path to the first occurrence of the file or folder, or None if not found.
        find_all_items(): list: A list of paths to all occurrences of the file or folder. Returns an empty list if none are found.
"""

# Function to find the first occurrence of a file or folder
def find_item(name, search_directory='.', skip_dirs=None, search_for=None):
    for root, dirs, files in os.walk(search_directory):
        # Skip specific folders
        if skip_dirs:
            dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        # Search for files
        if search_for is None or search_for == 'file':
            if name in files:
                return os.path.join(root, name)
        
        # Search for folders
        if search_for is None or search_for == 'folder':
            if name in dirs:
                return os.path.join(root, name)
    
    return None

# Function to find all occurrences of a file or folder
def find_all_items(name, search_directory='.', skip_dirs=None, search_for=None):
    matches = []

    for root, dirs, files in os.walk(search_directory):
        # Skip specific folders
        if skip_dirs:
            dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        # Search for files
        if search_for is None or search_for == 'file':
            if name in files:
                matches.append(os.path.join(root, name))
        
        # Search for folders
        if search_for is None or search_for == 'folder':
            if name in dirs:
                matches.append(os.path.join(root, name))

    return matches

# Example usage
if __name__ == "__main__":
    # Find all occurrences of 'employee_list' (could be a file or folder)
    matching_paths = find_all_items('employee_list.txt', skip_dirs=['outputs', 'logs'], search_for=None)
    if matching_paths:
        for path in matching_paths:
            print(f"Item found at: {path}")
    else:
        print("Item not found")
