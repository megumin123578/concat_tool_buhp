# auto_runner.py
import time
import subprocess

while True:
    print("Running be_ca.py ...")
    try:
        subprocess.run(["python", "be_ca.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    time.sleep(30)

    print("Running bluey.py ...")
    try:
        subprocess.run(["python", "bluey.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    time.sleep(30)

    print("Running spidey.py ...")
    try:
        subprocess.run(["python", "spidey.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    time.sleep(30) 

    print("Running maycay.py ...")
    try:
        subprocess.run(["python", "maycay.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    time.sleep(30) 

    print("Running findtoys.py ...")
    try:
        subprocess.run(["python", "findtoys.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    time.sleep(30) 

    print("Running bluey_funtoys.py ...")
    try:
        subprocess.run(["python", "bluey_funtoys.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
    time.sleep(30) 