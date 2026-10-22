#!/bin/bash
# Script tự động cấu hình Web Server khi khởi tạo Instance (User Data / Cloud-Init)
apt-get update -y
apt-get install -y nginx

# Lấy địa chỉ IP chính của máy ảo
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Cấu hình file index.html hiển thị thông tin nhóm và IP máy ảo
cat <<EOF > /var/www/html/index.html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Web Server - NT533.R12.G12</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; background-color: #f4f6f9; }
        .card { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; }
        h2 { color: #27ae60; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Nhom 12 - NT533.R12.G12</h1>
        <h2>Day la web server cua VM: ${LOCAL_IP}</h2>
    </div>
</body>
</html>
EOF

systemctl restart nginx
systemctl enable nginx

