# nftables-set-manager

This is a small set of scripts and modules that ease management of named set in [nftables](https://wiki.nftables.org)

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
