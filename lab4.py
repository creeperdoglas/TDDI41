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
    print(f"Skapar användare {username}...")
    try:
        # Skapa användarkonto
        subprocess.run(['useradd', '-m', '-s', '/bin/bash', username], check=True)
        print(f"Användare {username} skapad.")

        # Sätt lösenord via pipe till chpasswd för säker hantering
        passwd_input = f'{username}:{password}'
        subprocess.run(['chpasswd'], input=passwd_input, text=True, check=True)
        print(f"Lösenord satt för {username}.")
    except subprocess.CalledProcessError as e:
        print(f"Fel uppstod när användaren {username} skapades: {e}")
        sys.exit(1)


def test_root_user_exists():
    """Testfall för att verifiera att användaren 'root' existerar"""
    if user_exists('root'):
        print("Test 1: Användaren 'root' existerar - OK")
    else:
        print("Test 1: Användaren 'root' saknas - FAIL")
        sys.exit(1)

def test_games_user_noshell():
    """Testfall för att verifiera att användaren 'games' inte har ett giltigt skal"""
    try:
        shell = subprocess.run(['getent', 'passwd', 'games'], capture_output=True, text=True)
        if shell.returncode == 0:
            user_shell = shell.stdout.strip().split(':')[-1]
            if user_shell in ['/usr/sbin/nologin', '/bin/false']:
                print("Test 2: Användaren 'games' har inget giltigt skal - OK")
            else:
                print(f"Test 2: Användaren 'games' har ett giltigt skal ({user_shell}) - FAIL")
                sys.exit(1)
        else:
            print("Test 2: Användaren 'games' finns inte - FAIL")
            sys.exit(1)
    except Exception as e:
        print(f"Fel vid kontroll av skal för användaren 'games': {e}")
        sys.exit(1)

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

    # Kör testerna efter att användare har skapats
    print("\n-- Kör testerna --")
    test_root_user_exists()
    test_games_user_noshell()

if __name__ == "__main__":
    main()