#!/usr/bin/env python3
import os
import random
import string
import subprocess
import sys

LDAP_BASE_DN = "dc=grupp13,dc=liu,dc=se"
LDAP_USER_OU = "ou=users"
LDAP_ADMIN_DN = "cn=admin," + LDAP_BASE_DN
LDAP_PASSWORD_FILE = "/etc/ldapscripts/ldapscripts.passwd"  # Fil med lösenord för LDAP-bindning


def generate_username(full_name):
    parts = full_name.split()
    if len(parts) >= 2:
        username = (parts[0][0] + parts[1]).lower()
    else:
        username = parts[0].lower()

    username = ''.join(filter(str.isalnum, username))[:8]

    if not username.isascii():
        print(f"Ogiltigt namn, felaktiga tecken i {full_name}, skapar slumpmässigt istället.")
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
    return ''.join(random.choices(characters, k=length))


def add_user_to_ldap(username, full_name, password):
    print(f"Lägger till användare {username} i LDAP...")
    uid_number = find_next_uid_number()
    if not uid_number:
        print("Kunde inte hitta nästa lediga UID-nummer.", file=sys.stderr)
        sys.exit(1)

    ldif = f"""
dn: uid={username},{LDAP_USER_OU},{LDAP_BASE_DN}
objectClass: inetOrgPerson
objectClass: posixAccount
objectClass: shadowAccount
cn: {full_name}
sn: {full_name.split()[-1]}
uid: {username}
uidNumber: {uid_number}
gidNumber: {uid_number}
homeDirectory: /home/{username}
loginShell: /bin/bash
userPassword: {password}
    """
    try:
        result = subprocess.run(
            ['ldapadd', '-D', LDAP_ADMIN_DN, '-y', LDAP_PASSWORD_FILE, '-H', 'ldap://localhost'],
            input=ldif,
            text=True,
            check=True
        )
        print(f"Användare '{username}' har lagts till i LDAP.")
    except subprocess.CalledProcessError as e:
        print(f"Fel uppstod när användaren {username} skulle läggas till i LDAP: {e}")
        sys.exit(1)


def find_next_uid_number(start_uid=1001):
    # Sök efter nästa lediga UID
    try:
        result = subprocess.run(
            ['ldapsearch', '-x', '-LLL', '-b', f'{LDAP_USER_OU},{LDAP_BASE_DN}', 'uidNumber'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("Kunde inte hämta UID-nummer från LDAP.")
            return None

        uids = [int(line.split(': ')[1]) for line in result.stdout.splitlines() if line.startswith('uidNumber')]
        return max(uids, default=start_uid - 1) + 1
    except Exception as e:
        print(f"Ett fel uppstod vid sökning av UID-nummer: {e}")
        return None


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
        add_user_to_ldap(username, name, password)

    print("\nAlla användare har lagts till i LDAP.")


if __name__ == "__main__":
    main()
