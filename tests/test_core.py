import sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atelpix.store import LocalStore
from atelpix.security import SecurityError, verify_totp, totp_code, DB_MAGIC, decrypt_container


def test_owner_setup_login_and_encryption(tmp_path):
    p=tmp_path/'clients.atdb'; s=LocalStore(p)
    secret=s.setup('CorrectHorseBatteryStaple!2026')
    codes=s.generate_recovery_codes()
    assert p.read_bytes().startswith(DB_MAGIC)
    assert b'CorrectHorseBatteryStaple' not in p.read_bytes()
    assert verify_totp(secret,totp_code(secret))
    s.close()
    s=LocalStore(p)
    try: s.unlock('wrong password long enough')
    except SecurityError: pass
    else: assert False, 'wrong password accepted'
    s.unlock('CorrectHorseBatteryStaple!2026')
    assert s.verify_second_factor(totp_code(secret))
    assert s.verify_second_factor(codes[0], recovery=True)
    assert not s.verify_second_factor(codes[0], recovery=True)
    s.close()


def test_client_crud_search_and_persistence(tmp_path):
    p=tmp_path/'db.atdb'; s=LocalStore(p); s.setup('CorrectHorseBatteryStaple!2026')
    s.save_client({'name':'Acme Studio','country':'Canada','city':'Toronto','timezone':'America/Toronto','email':'hello@example.com','phone':'+1 416 555 0100','status':'Active'})
    assert len(s.list_clients('Acme')) == 1
    assert len(s.list_clients('', 'Active')) == 1
    assert len(s.list_clients('', 'Inactive')) == 0
    cid=s.list_clients()[0][0]
    s.save_client({'name':'Acme Updated','country':'Canada','city':'Toronto','timezone':'America/Toronto','email':'hello@example.com','phone':'+1 416 555 0100','status':'Active'},cid)
    assert s.list_clients('Updated')[0][1] == 'Acme Updated'
    s.delete_client(cid); assert len(s.list_clients()) == 0
    s.close(); s=LocalStore(p); s.unlock('CorrectHorseBatteryStaple!2026')
    assert len(s.list_clients()) == 0
    s.close()


def test_clocks_and_backup_restore(tmp_path):
    p=tmp_path/'db.atdb'; s=LocalStore(p); secret=s.setup('CorrectHorseBatteryStaple!2026')
    s.save_client({'name':'Backup Client','country':'US','status':'Active'})
    backup=tmp_path/'good.atbak'; s.backup(backup)
    cid=s.list_clients()[0][0]; s.delete_client(cid)
    s.restore(backup,'CorrectHorseBatteryStaple!2026','CorrectHorseBatteryStaple!2026')
    assert s.list_clients()[0][1] == 'Backup Client'
    try: s.restore(backup,'WrongPasswordForBackup!','CorrectHorseBatteryStaple!2026')
    except SecurityError: pass
    else: assert False, 'wrong backup password accepted'
    s.add_clock('Auckland','New Zealand','Pacific/Auckland')
    assert any(row[3]=='Pacific/Auckland' for row in s.clocks())
    try: s.add_clock('Bad','Nowhere','Not/AZone')
    except ValueError: pass
    else: assert False, 'invalid time zone accepted'
    s.close()


def test_password_change(tmp_path):
    p=tmp_path/'db.atdb'; s=LocalStore(p); s.setup('CorrectHorseBatteryStaple!2026')
    s.change_password('CorrectHorseBatteryStaple!2026','AnotherStrongPassword!2026')
    s.close(); s=LocalStore(p); s.unlock('AnotherStrongPassword!2026'); s.close()


def test_restore_old_backup_after_password_change(tmp_path):
    p=tmp_path/'db.atdb'; s=LocalStore(p); s.setup('CorrectHorseBatteryStaple!2026')
    s.save_client({'name':'Historic Client'})
    backup=tmp_path/'historic.atbak'; s.backup(backup)
    s.change_password('CorrectHorseBatteryStaple!2026','NewCurrentPassword!2026')
    s.save_client({'name':'Newer Client'})
    s.restore(backup,'CorrectHorseBatteryStaple!2026','NewCurrentPassword!2026')
    assert [r[1] for r in s.list_clients()] == ['Historic Client']
    s.close()


def test_rate_limit_and_dst_zoneinfo(tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    p=tmp_path/'db.atdb'; s=LocalStore(p); s.setup('CorrectHorseBatteryStaple!2026'); s.close()
    s=LocalStore(p)
    for _ in range(5):
        try: s.unlock('WrongPasswordThatIsLongEnough!')
        except SecurityError: pass
    try: s.unlock('WrongPasswordThatIsLongEnough!')
    except SecurityError as e: assert 'Too many attempts' in str(e)
    else: assert False, 'rate limiter did not engage'
    winter=datetime(2026,1,15,tzinfo=ZoneInfo('America/New_York')).utcoffset()
    summer=datetime(2026,7,15,tzinfo=ZoneInfo('America/New_York')).utcoffset()
    assert winter != summer


def test_tamper_detection_and_backup_schedule(tmp_path):
    p=tmp_path/'db.atdb'; s=LocalStore(p); s.setup('CorrectHorseBatteryStaple!2026')
    assert s.backup_due() is True
    s.save_client({'name':'Confidential Client Name'})
    assert b'Confidential Client Name' not in p.read_bytes()
    backup=tmp_path/'backup.atbak'; s.backup(backup)
    assert s.backup_due() is False
    damaged=bytearray(backup.read_bytes()); damaged[-1] ^= 0x01; bad=tmp_path/'damaged.atbak'; bad.write_bytes(damaged)
    try: s.restore(bad,'CorrectHorseBatteryStaple!2026','CorrectHorseBatteryStaple!2026')
    except SecurityError: pass
    else: assert False, 'tampered backup accepted'
    assert s.list_clients()[0][1] == 'Confidential Client Name'
    s.close()
