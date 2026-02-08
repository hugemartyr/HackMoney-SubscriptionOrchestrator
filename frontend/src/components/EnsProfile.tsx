"use client";

import { useAccount, useEnsName, useEnsAvatar } from 'wagmi'
import { mainnet } from 'wagmi/chains'

export function EnsProfile() {
    const { address } = useAccount()

    const { data: ensName } = useEnsName({
        address,
        chainId: mainnet.id,
    })

    const { data: ensAvatar } = useEnsAvatar({
        name: ensName ?? undefined,
        chainId: mainnet.id,
    })

    if (!address) return null

    const truncatedAddress = `${address.slice(0, 6)}...${address.slice(-4)}`
    const displayName = ensName ?? `User-${address.slice(2, 6)}`

    return (
        <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 rounded-full px-3 py-1 scale-90 origin-right">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-yellow-400 to-orange-500 overflow-hidden flex items-center justify-center text-[10px] font-bold text-black border border-white/20">
                {ensAvatar ? (
                    <img src={ensAvatar} alt={displayName} className="w-full h-full object-cover" />
                ) : (
                    address.slice(2, 4).toUpperCase()
                )}
            </div>
            <div className="flex flex-col">
                <span className="text-xs font-semibold text-white leading-none">{displayName}</span>
                {!ensName && <span className="text-[10px] text-gray-400 leading-none mt-0.5">{truncatedAddress}</span>}
            </div>
        </div>
    )
}
