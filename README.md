# nftables-set-manager

This is a small set of scripts and modules that ease management of named sets in [nftables](https://wiki.nftables.org)

### Overview

Named sets in nftables provide a good way to enable dynamically adjusting data sets in the firewall.

A good example of this is mantaining IP address whitelists of the various services that your server may need to contact, in order to restrict outbound traffic from the server to only those IP addresses. However, the IP address of, say, ```api.example.com``` may change in a way that's out of your control. One way to manage this is to periodically issue a DNS query, get the current IP address, and update the named set for that whitelist accordingly.

```nftables-set-manager``` handles the management of the sets based upon:

1. A simple [YAML](https://yaml.org/) configuration file
2. Re-usable plugins that handle building the updated elements of a particular configured set

Several plugins come with the pagkage:

 * resolv: Extracts IP elements for nameservers from ```/etc/resolv.conf```
 * dns: Gets the IP address(es) of a hostname (requires berserker_resolver package)
 * apt_list: Gets IP addresses for all Apt sources files (requires berserker_resolver package)
 * s3_ips: Gets IP addresses for AWS S3 regions
 * github_ips: Gets IP addresses for Github IP types
 * google_cloud_ips: Gets IP addresses for Google Cloud services

...and it's easy to write additional ones for your needs.

### Usage

1. Create the named sets in your nftables configuration, e.g.
    ```sh
    nft add table inet filter
    nft add set inet filter dns_ips { type ipv4_addr\;}
    ```
 2. Create a ```config.yaml``` (see  [config.sample.yaml](config.sample.yaml) for format), and configure the sets you want to manage
 3. Run ```manage-sets.py --help``` to see the arguments for the script
 4. See [plugins/example.py](plugins/example.py) for an example of how to write a custom plugin.
 5. Consider setting up a cron job to automatically update your sets
 
 #### Caveats
 
  * The named sets themselves are not managed by this code
