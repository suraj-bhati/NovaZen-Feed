cat > restart.sh << 'EOF'
#!/bin/bash
# A simple script to restart the NovaZen Feed service and check its status.

echo "--> Restarting the NovaZen Feed Service..."
sudo systemctl restart novazen_feed.service

echo ""
echo "--> Waiting for 2 seconds to allow the service to start..."
sleep 2

echo "--> Current status of the service:"
sudo systemctl status novazen_feed.service --no-pager

echo ""
echo "--> To view the live logs, run this command:"
echo "sudo journalctl -u novazen_feed.service -f"
EOF
