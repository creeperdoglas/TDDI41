#!/usr/bin/env python3
import os
import random
import string
import subprocess
import sys

def generate_username(full_name):
    parts = full_name.split()
    if len(parts) >= 2:
        username = (parts[0][0] + parts[1]).lower()
    else:
        username = parts[0].lower()

    username = ''.join(filter(str.isalnum, username))[:8]

    if not username.isascii():
        print(f"Ogiltigt namn, felaktiga tecken i {full_name}, skapar slumpmässigt istället")
        username = generate_random_username()

    while user_exists(username):
        suffix = ''.join(random.choices(string.digits, k=2))
        username = username[:6] + suffix

    return username

def generate_random_username(length=8):
    letters_and_digits = string.ascii_lowercase + string.digits
    return ''.join(random.choices(letters_and_digits, k=length))

def user_exists(username):
    try:
        result = subprocess.run(['id', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"Timeout vid kontroll av användare: {username}")
        return False
    except Exception as e:
        print(f"Ett fel uppstod vid kontroll av användare {username}: {e}")
        return False

def generate_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choices(characters, k=length))
    return password

def add_user(username, password):
    print(f"Lägger till användare {username} i LDAP...")
    try:
        # Skapa användare i LDAP
        subprocess.run(['ldapadduser', username, 'users'], check=True)
        print(f"Användare {username} tillagd i LDAP.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid skapande av användare {username}: {e}")
        sys.exit(1)

    try:
        password_input = f"{password}\n{password}\n"  # Skapa inmatning med lösenordet två gånger
        subprocess.run(['ldapsetpasswd', username], input=password_input, text=True, check=True)
        print(f"Lösenord för användare {username} satt i LDAP med setpasswd.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid sättande av lösenord för {username} med setpasswd: {e}")
        sys.exit(1)
    
    print(f"Användare '{username}' har skapats med lösenord: {password}")


def main():
    if len(sys.argv) != 2:
        print(f"Användning: {sys.argv[0]} <fil med namn>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, 'r') as file:
            names = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Filen '{filename}' hittades inte!", file=sys.stderr)
        sys.exit(1)

    for name in names:
        username = generate_username(name)
        password = generate_password()
        add_user(username, password)


if __name__ == "__main__":
    main()