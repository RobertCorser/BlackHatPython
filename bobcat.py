#!/usr/bin/python3
# bobcat.py
# Author: Robert Corser
# Source code modified from "Black Hat Python" by Justin Zeitz, published by No Starch Press
# TODO Add command history support (Up arrow to get previous commands)
# TODO Type command and have it appear next to prompt (E.g <bobcat:#> command)


import sys
import socket
import getopt
import threading
import subprocess

# Define global variables
listen = False
command = False
upload = False
execute = ""
target = ""
upload_dest = ""
port = 0


def usage():
    print("Bobcat Net Tool")
    print()
    print("Usage: bobcat.py -t target_host -p port")
    print("-l --listen                  -listen on [host]:[port] for incoming connections")
    print("-e, --execute=file_to_run    -execute the given file upon receiving a connection")
    print("-c --command                 -initalize a command shell")
    print("-u --upload=destination      -upon receiving connection, upload a file and write to [destination]")
    print()
    print()
    print("Examples:")
    print("bobcat.py -t 192.168.0.1 -p 5555 -l -c")
    print("bobcat.py -t 192.168.0.1 -p 5555 -l -u=C:\\target.exe")
    print("bobcat.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'ABCDEFGHI' | ./bhpnet.py -t 192.168.11.12 -p 135")
    sys.exit(0)


def main():
    global listen
    global port
    global execute
    global command
    global upload_dest
    global target

    if not len(sys.argv[1:]):
        usage()

    # Read command line arguments
    try:
        opts, arge = getopt.getopt(sys.argv[1:], "hle:t:p:cu:",
                                   ["help", "listen", "execute", "target", "port", "command", "upload"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--command"):
            command = True
        elif o in ("-u", "--upload"):
            upload_dest = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        else:
            assert False, "Unhandled Option"

    # Are we going to listen or just send data from stdin?
    if not listen and len(target) and port > 0:

        # Read in buffer from command line
        # This will block, so send CTRL-D if not sending input to stdin
        buffer = sys.stdin.read()

        # Send data off
        client_sender(buffer)

    # We are going to listen and perform commands depending on command line options
    if listen:
        server_loop()


def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to target host
        client.connect((target, port))

        if len(buffer):
            client.send(buffer.encode('utf-8'))
        while True:
            # Wait for data
            recv_len = 1
            response = ""

            while recv_len:
                data = client.recv(4096).decode('utf-8')
                recv_len = len(data)
                response += data

                if recv_len < 4096:
                    break

            print(response)

            # Wait for more input
            buffer = input("")
            buffer += "\n"

            # Send it off
            client.send(buffer.encode('utf-8'))
    except:
        print("[*] Exception! Exiting")
        # Teardown connection
        client.close()


def server_loop():
    global target

    # If no target is defined, we listen on all interfaces
    if not len(target):
        target = "0.0.0.0"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)

    while True:
        client_socket, addr = server.accept()

        # Create thread to handle new client
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()


def run_command(command):
    # Trim newline
    command = command.rstrip()

    # Run command and get output
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except:
        output = b"Failed to execute command.\r\n"

    # Send output back to client
    return output


def client_handler(client_socket):
    global upload
    global execute
    global command

    # Check for upload
    if len(upload_dest):

        # Read in all of the bytes and write to our destination
        file_buffer = ""

        # Keep reading until no data is available
        while True:
            data = client_socket.recv(1024).decode('utf-8')

            if not data:
                break
            else:
                file_buffer += data

        # Now we take these bytes and try to write them
        try:
            file_descriptor = open(upload_dest,"wb")
            file_descriptor.write(file_buffer)
            file_descriptor.close()

            # Acknowledge that we wrote the file
            client_socket.send(b"Successfully saved file to %s\r\n" % upload_dest)
        except:
            client_socket.send(b"Failed to save file to %s\r\n" % upload_dest)

    # Check for command execution
    if len(execute):

        # Run the command
        output = run_command(execute)

        client_socket.send(output.encode('utf-8'))

    # Check if shell was requested
    if command:

        while True:
            # Show a prompt
            client_socket.send(b"<bobcat:#> ")

            # Receive until newline (enter key)
            cmd_buffer = ""
            while "\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024).decode('utf-8')

            # Send back the command output
            response = run_command(cmd_buffer)
            client_socket.send(response)


main()
