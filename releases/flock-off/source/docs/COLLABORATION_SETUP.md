<!-- SPDX-License-Identifier: Apache-2.0 -->
# Self-hosted collaboration setup

The relay is software you operate, not an existing hosted service. This guide does not install Tor, provision hosting, open firewall ports or configure services. The application protocol is new and not independently audited; neither Tor nor room aliases guarantee anonymity. Live Tor and IP-leak behavior require separate validation.

## Relay operator

Use the installed Python environment:

```text
python -m flockoff_collaboration.cli provision --database relay.db --output room-provision.json
python -m flockoff_collaboration.cli serve --database relay.db --port 8765
```

Provisioning creates one room and a private file containing its room ID and administration capability. It uses exclusive file creation and restrictive platform permissions; existing output is never overwritten. Capabilities are not printed. Keep the provisioning file private and deliver it only to the room owner through a trusted channel. Keep the relay database private too. The relay stores capability hashes and opaque packets, not owner signing keys. Its storage is bounded; capacity exhaustion rejects new work. A failed output write after room allocation can leave an unused room consuming capacity; do not repeat provision blindly.

The server always binds `127.0.0.1`. There is no `--host` override. Ports must be 1–65535. Ctrl+C stops and closes the server/database. Avoid competing administrative processes on the same database.

An operator must separately configure their own Tor v3 onion service to forward its HTTP port to this local listener, using the [official Tor onion-service setup guidance](https://community.torproject.org/onion-services/setup/). Do not expose the listener through a public reverse proxy or substitute a clearnet endpoint. Client transport accepts only a validated onion endpoint and uses local SOCKS5h, with no direct fallback. The default local Tor SOCKS port is 9050. This application does not install, launch or reconfigure Tor.

## Owner and participants

In Shared room → Owner administration, create a separate owner vault and external key, enter the onion endpoint, and initialize using the provisioning file. The owner signing secret stays on that endpoint in the encrypted local vault; it is never given to the relay. Back up the vault and key separately.

A participant creates a separate room workspace and saves its public join-request file. The owner imports the request, checks the alias/signing fingerprint through a trusted channel, and writes a sealed invitation. The participant imports that file and explicitly verifies the owner fingerprint, endpoint and room preview. Invitations expire after five minutes and membership changes invalidate pending invitations; issue and accept sequentially.

The owner must explicitly start its app-active service and remain online for joins and fresh send authorizations. A participant separately chooses room sharing scopes and consents to app-active automatic sync. No startup upload occurs. If the owner is unavailable, the participant displays `Room owner offline: saved locally, sync queued`. Selected structured cards are shared; private notebooks, original files and council identity are not automatically included.

Removing a member blocks new grants and invalidates pending invites. It cannot recall plaintext/ciphertext already copied or an already authorized in-flight batch within the bounded grant window. The relay can delay or censor traffic. Read the [Tor traffic-correlation limitations](https://support.torproject.org/about-tor/security/attacks-on-onion-routing/) before making privacy claims. Local synthetic tests establish software behavior, not real-world anonymity.
