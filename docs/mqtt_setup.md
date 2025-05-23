# MQTT Broker Setup

This document discusses the setup of the MQTT broker used in SBCSE.


## Install the Mosquitto MQTT Broker

The steps below explain the installation of Mosquitto MQTT broker on macOS, but several steps are also valid for other operating systems.

1. Install Homebrew:
```bash　
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Use Homebrew to install Mosquitto:
```bash
brew install mosquitto
```

3. Start/Restart Mosquitto:
```bash
brew services start mosquitto
brew services restart mosquitto
```

4. Test Mosquitto:
```bash
# Use one terminal window to subscribe to a topic:
mosquitto_sub -h localhost -t test
# Publish a message to that topic in another terminal window:
mosquitto_pub -h localhost -t test -m "Hello, MQTT\!"
```

5. Stop Mosquitto:
```bash
brew services stop mosquitto
```

6. Install the library `paho-mqtt`:
```bash 
pip install paho-mqtt
```

7. Modify the configuration file:
```bash
#bind_address ip-address/host name
bind_address 127.0.0.1
#Port to use for the default listener
port 1883
```


## Generate the MQTTS Certificates

The steps below explain how to generate the secure certificates needed when using the MQTTS protocol in SBCSE.

1. Generate the CA private key and certificate:
```bash
openssl genpkey -algorithm RSA -out ca.key
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=CA"
```

2. Generate the server private key and Certificate Signing Request (CSR):
```bash
openssl genpkey -algorithm RSA -out server.key
openssl req -new -key server.key -out server.csr -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=localhost"
```

3. Sign the server certificate:
```bash
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 3650
```

4. Generate the client private key and certificate signing request (CSR):
```bash
openssl genpkey -algorithm RSA -out client.key
openssl req -new -key client.key -out client.csr -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=client"
```

5. Sign the client certificate:
```bash
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 3650
```


## Configure the Mosquitto MQTT Broker

The steps below explain how to configure the Mosquitto MQTT broker used in SBCSE.

1. Move the generated certificates to the appropriate directory:
```bash
# Create a directory to store the certificate
sudo mkdir -p /usr/local/etc/mosquitto/certs
sudo mv ca.crt /usr/local/etc/mosquitto/certs/
sudo mv server.crt /usr/local/etc/mosquitto/certs/
sudo mv server.key /usr/local/etc/mosquitto/certs/
```

2. Add the following information to the `mosquitto.conf` file:
```bash
# Default listener on port 1883 for non-encrypted connections
listener 1883
# Secure listener on port 8883 for encrypted connections
listener 8883

cafile /usr/local/etc/mosquitto/certs/ca.crt
certfile /usr/local/etc/mosquitto/certs/server.crt
keyfile /usr/local/etc/mosquitto/certs/server.key

require_certificate true
tls_version tlsv1.2

# Log file settings
log_dest file /usr/local/var/log/mosquitto/mosquitto.log
log_type all
allow_anonymous true
```

3. Restart Mosquitto:
```bash
brew services restart mosquitto
```

4. Check the process and execution logs to confirm that the configuration was successful:
```bash
sudo netstat -tulnp | grep mosquitto
tail -f /var/log/mosquitto/mosquitto.log
```

5. Validate the configurations:
```bash
# Check that the paths to cafile, certfile, and keyfile are correct
ls -l /usr/local/etc/mosquitto/certs/

# View firewall
sudo pfctl -d

# Check that the mostquitto service is not running
brew services list

# Check if Mosquitto is listening on the port
lsof -iTCP:1883 -sTCP:LISTEN
lsof -iTCP:8883 -sTCP:LISTEN
```
