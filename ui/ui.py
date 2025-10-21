import core.file_search as fs

def main():
    filename = input("Enter the filename: ")
    files = fs.find(filename, "~")
    for file in files:
        print(file)
    if len(files) == 0:
        print("I didn't find anything, would you like to try searching the whole disk?")
        answer = input("(y/n): ")
        if answer.lower() == 'y':
            files = fs.find(filename)
            if len(files) == 0:
                print("No files found on the whole disk.")
            else:
                for file in files:
                    print(file)

if __name__ == "__main__":
    main()