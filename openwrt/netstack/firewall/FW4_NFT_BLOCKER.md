# fw4/nftables blocker (OpenWrt x86/64 VM)

## Symptom
Restarting firewall (`/etc/init.d/firewall restart`) fails with:

```
Error: Chain of type "filter" is not supported, perhaps kernel support is missing?
  type filter hook input priority filter; policy drop;
```

Observed on VP2430 OpenWrt VM (Proxmox) after upgrades:
- OpenWrt 24.10.0 (kernel 6.6.73)
- OpenWrt 24.10.4 (kernel 6.6.110)

In both cases, `/lib/modules/<kernel>/` contains `nft_chain_nat.ko` but no `nft_chain_filter.ko`,
and the kernel appears unable to accept filter-hook chains.

## Impact
- `fw4` cannot load rules → `firewall` service cannot be relied on.
- Anything depending on fw4 (masquerade, zone rules) must be provided another way.

## MVP workaround (iptables-legacy)
Until we resolve the kernel/nft support, RoamCore applies a minimal NAT+forwarding ruleset via iptables.

Files:
- `openwrt/netstack/firewall/iptables_mvp.sh`
- `openwrt/netstack/firewall/roamcore-fw.init`

This is sufficient to:
- NAT LAN+USER out via the current uplink
- Keep mwan3 + RoamCore API + HA polling functional

## Next investigations
1) Validate if this is specific to the current OpenWrt image type (combined squashfs) or to Proxmox.
2) Try alternative OpenWrt images (EFI vs non-EFI, ext4 vs squashfs) if kernel config differs.
3) If kernel config truly lacks `CONFIG_NFT_CHAIN_FILTER`, the fix is a different kernel build.

If this remains unresolved, keep the MVP workaround and revisit when we move to a known-good golden image.

