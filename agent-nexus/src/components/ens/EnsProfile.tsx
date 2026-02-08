import { useAccount, useEnsName, useEnsAvatar } from 'wagmi'
import { Avatar, AvatarImage, AvatarFallback } from '../ui/avatar'

interface EnsProfileProps {
    /** Optional address to display. If not provided, uses the connected account. */
    address?: `0x${string}`
    /** Whether to show the truncated address below the ENS name */
    showAddress?: boolean
    /** Custom class name for styling */
    className?: string
}

/**
 * Displays an ENS profile with avatar and name for the connected user or a specified address.
 * Falls back to truncated address display if no ENS name is found.
 */
export function EnsProfile({ address: propAddress, showAddress = true, className = '' }: EnsProfileProps) {
    const { address: connectedAddress } = useAccount()
    const address = propAddress ?? connectedAddress

    const { data: ensName, isLoading: nameLoading } = useEnsName({
        address,
        chainId: 1
    })

    const { data: ensAvatar, isLoading: avatarLoading } = useEnsAvatar({
        name: ensName ?? undefined,
        chainId: 1
    })

    if (!address) return null

    const truncatedAddress = `${address.slice(0, 6)}...${address.slice(-4)}`
    const displayName = ensName ?? truncatedAddress
    const isLoading = nameLoading || avatarLoading

    return (
        <div className={`flex items-center gap-3 ${className}`}>
            <Avatar className="h-10 w-10">
                {ensAvatar && <AvatarImage src={ensAvatar} alt={displayName} />}
                <AvatarFallback className="bg-gradient-to-br from-primary/20 to-primary/40 text-primary font-medium">
                    {address.slice(2, 4).toUpperCase()}
                </AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
                <span className={`font-semibold ${isLoading ? 'animate-pulse' : ''}`}>
                    {isLoading ? '...' : displayName}
                </span>
                {showAddress && ensName && (
                    <span className="text-sm text-muted-foreground">
                        {truncatedAddress}
                    </span>
                )}
            </div>
        </div>
    )
}
