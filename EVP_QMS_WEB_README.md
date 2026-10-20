EVP ISO 9001:2015 QMS - Web Version

1. Install Python 3.11-3.14 recommended.
2. In Terminal:
   python3 -m pip install -r requirements.txt
3. Start:
   python3 EVP_QMS_Web.py
4. On the same Mac open:
   http://127.0.0.1:5000
5. Initial login:
   Username: admin
   Password: admin123
   Change this initial password/security setup before production use.

MULTI-USER OFFICE NETWORK
The app listens on 0.0.0.0:5000. Other computers on the same network can browse to:
   http://<server-mac-ip>:5000
macOS Firewall may ask you to allow incoming connections.

PRODUCTION NOTE
This is a Version 1 web application. For real company-wide production deployment, use PostgreSQL, HTTPS, a production WSGI server/reverse proxy, password reset/change, granular permissions, automatic backups, file attachments, electronic approvals, and stronger security controls.
