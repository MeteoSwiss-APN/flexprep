# Aviso Setup Guide

## Documentation

To set up Aviso on the EWC, follow the steps in the documentation:

1. [Aviso Notification System on EWC (Points 1 and 2)](https://confluence.ecmwf.int/display/EWCLOUDKB/Aviso+Notification+System+on+EWC)
2. [Create a config file (Section 2.2)](https://confluence.ecmwf.int/display/UDOC/Setting+up+Aviso+Notification+System+for+ECMWF%27+events)

## Configuration

1. After creating the `~/.marsrc/mars.email` and `~/.marsrc/mars.token` files as outlined in Section 2.2 of the documentation, save the `config.yaml` and e.g. `listener_diss.yaml` file under `~/.aviso/`.
2. Ensure the paths in the `config.yaml` file are relevant and exist on your machine.

## Running Aviso as a Service

Refer to the [documentation](https://confluence.ecmwf.int/display/EWCLOUDKB/Aviso+Notification+System+on+EWC) for detailed instructions.

To apply changes made to the `~/.aviso/config.yaml` file, restart the Aviso service:

```bash
sudo systemctl restart aviso.service
```
## Replaying Notifications
To replay notifications for a specific time range, use the following command:

```bash
aviso listen --from 2020-01-20T00:00:00.0Z --to 2020-01-22T00:00:00.0Z
```