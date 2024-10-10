#!/usr/bin/env python3
import os
import random
import string
import subprocess
import sys

def generate_username(full_name):
    # Generera ett användarnamn som baseras på personens namn.
    parts = full_name.split()
    if len(parts) >= 2:
        username = (parts[0][0] + parts[1]).lower()  # Förnamnsinitial + efternamn
    else:
        username = parts[0].lower()  # Om bara ett namn finns, använd det

    # Begränsa längden och ta bort ogiltiga tecken.
    username = ''.join(filter(str.isalnum, username))[:8]

    # Lägg till slumpmässiga siffror om användarnamnet redan används
    while user_exists(username):
        suffix = ''.join(random.choices(string.digits, k=2))
        username = username[:6] + suffix

    return username

def user_exists(username):
    try:
        # Kontrollera om användaren existerar med en timeout för att undvika hängande process
        result = subprocess.run(['id', username], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        return result.returncode == 0  # Om kommandot returnerar 0, finns användaren
    except subprocess.TimeoutExpired:
        print(f"Timeout vid kontroll av användare: {username}")
        return False
    except Exception as e:
        print(f"Ett fel uppstod vid kontroll av användare {username}: {e}")
        return False


def generate_password(length=12):
    # Generera ett slumpmässigt lösenord med bokstäver, siffror och specialtecken.
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choices(characters, k=length))
    return password

def add_user(username, password):
    # Skapa användarkonto med hemkatalog.
    try:
        subprocess.run(['sudo', 'useradd', '-m', '-s', '/bin/bash', username], check=True)
        
        # Använd subprocess för att sätta lösenordet genom en pipe.
        subprocess.run(['echo', f'{username}:{password}'], check=True, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(['sudo', 'chpasswd'], input=f'{username}:{password}', text=True, check=True)

        print(f"Användare '{username}' har skapats med lösenord: {password}")
    except subprocess.CalledProcessError as e:
        print(f"Fel uppstod när användaren '{username}' skapades: {e}", file=sys.stderr)

def main():
    if len(sys.argv) != 2:
        print(f"Användning: {sys.argv[0]} <fil med namn>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]

    # Läs in namnen från filen
    try:
        with open(filename, 'r') as file:
            names = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Filen '{filename}' hittades inte!", file=sys.stderr)
        sys.exit(1)

    # Skapa ett användarkonto för varje namn
    for name in names:
        username = generate_username(name)
        password = generate_password()
        add_user(username, password)

if __name__ == "__main__":
    main()

