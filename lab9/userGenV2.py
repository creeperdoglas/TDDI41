#!/usr/bin/env python3
import os
import random
import string
import subprocess
import sys


def generate_username(full_name):
    # Kontrollera om namnet innehåller endast ASCII-tecken
    if not full_name.isascii():
        print(f"Ogiltigt namn med icke-ASCII-tecken: {full_name}. Skapar slumpmässigt användarnamn.")
        return generate_random_username()

    # Generera användarnamn baserat på namnet
    parts = full_name.split()
    if len(parts) >= 2:
        username = (parts[0][0] + parts[1]).lower()
    else:
        username = parts[0].lower()

    username = ''.join(filter(str.isalnum, username))[:8]

    # Lägg till suffix om användarnamnet redan finns i LDAP
    original_username = username
    counter = 0
    while ldap_user_exists(username):
        counter += 1
        suffix = f"{counter:02d}"  # Tvåsiffrigt suffix
        username = original_username[:6] + suffix

    return username


def generate_random_username(length=8):
    """Generera ett slumpmässigt användarnamn."""
    letters_and_digits = string.ascii_lowercase + string.digits
    return ''.join(random.choices(letters_and_digits, k=length))


def ldap_user_exists(username):
    """Kontrollera om en användare redan finns i LDAP."""
    try:
        result = subprocess.run(
            ['ldapsearch', '-x', '-b', 'ou=users,dc=grupp13,dc=liu,dc=se', f'(uid={username})'],
            capture_output=True, text=True, timeout=5
        )
        if f"dn: uid={username}," in result.stdout:
            print(f"Användare {username} hittades i LDAP.")
            return True
        print(f"Användare {username} hittades INTE i LDAP.")
        return False
    except subprocess.TimeoutExpired:
        print(f"Timeout vid kontroll av användare: {username}")
        return False
    except Exception as e:
        print(f"Ett fel uppstod vid kontroll av användare {username}: {e}")
        return False


def generate_password(length=12):
    characters = string.ascii_letters + string.digits + "!@#$%^&*()-_+="
    return ''.join(random.choices(characters, k=length))


def get_uid_from_ldap(username):
    """
    Hämtar UID för en användare från LDAP efter att den har skapats.
    """
    try:
        result = subprocess.run(
            ['ldapsearch', '-x', '-b', 'ou=users,dc=grupp13,dc=liu,dc=se', f'(uid={username})', 'uidNumber'],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("uidNumber:"):
                return int(line.split(":")[1].strip())
        print(f"UID för användare {username} hittades inte.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Fel vid hämtning av UID från LDAP för {username}: {e}")
        sys.exit(1)


def add_user_to_ldap(username, password, home_directory):
    print(f"Lägger till användare {username} i LDAP...")

    try:
        # Skapa användarpost i LDAP
        subprocess.run(['ldapadduser', username, 'users'], check=True)
        print(f"Användare {username} tillagd i LDAP.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid skapande av användare {username} i LDAP: {e}")
        sys.exit(1)

    # Hämta UID från LDAP
    uid = get_uid_from_ldap(username)

    try:
        # Sätt lösenord i LDAP
        password_input = f"{password}\n{password}\n"
        subprocess.run(['ldapsetpasswd', username], input=password_input, text=True, check=True)
        print(f"Lösenord för användare {username} satt i LDAP.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid sättande av lösenord för {username}: {e}")
        sys.exit(1)

    # Nu skapar vi samma användare lokalt med samma UID och hemkatalog
    try:
        print(f"Skapar användare {username} lokalt med UID {uid}...")
        subprocess.run(['useradd', '-m', '-u', str(uid), '-s', '/bin/bash', '-d', f"{home_directory}/{username}", username], check=True)
        # Sätt det lokala lösenordet
        passwd_input = f'{username}:{password}'
        subprocess.run(['chpasswd'], input=passwd_input, text=True, check=True)
        print(f"Lokal användare {username} skapad med UID {uid} och lösenord satt.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid skapande av lokal användare {username}: {e}")
        sys.exit(1)

    # Uppdatera automount-poster i LDAP för att peka hemkatalogen till NFS
    try:
        with open('/etc/ldapscripts/ldapscripts.passwd', 'r') as secret_file:
            ldap_password = secret_file.read().strip()
        automount_dn = f"cn={username},ou=auto.home,ou=automount,ou=users,dc=grupp13,dc=liu,dc=se"
        automount_info = f"-fstype=nfs,rw,sync,vers=4 server.grupp13.liu.se:{home_directory}/{username}"

        ldif_content = f"""
dn: {automount_dn}
objectClass: automount
objectClass: top
cn: {username}
automountInformation: {automount_info}
"""
        subprocess.run([
            'ldapadd',
            '-x',
            '-D', 'cn=admin,dc=grupp13,dc=liu,dc=se',
            '-w', ldap_password
        ], input=ldif_content, text=True, check=True)
        print(f"Automount-poster för {username} uppdaterad.")
    except subprocess.CalledProcessError as e:
        print(f"Fel vid uppdatering av automount för {username}: {e}")
        sys.exit(1)

    print(f"Användare '{username}' har skapats i både LDAP och lokalt med lösenord: {password}")
    print(f"Hemkatalog för användare '{username}' är: {home_directory}/{username}")


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

        # Välj hemkatalog slumpmässigt mellan /home1 och /home2
        home_directory = random.choice(['/home1', '/home2'])

        add_user_to_ldap(username, password, home_directory)


if __name__ == "__main__":
    main()
