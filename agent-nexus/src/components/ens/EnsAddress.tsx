import { useEnsAddress, useEnsName, useEnsAvatar } from 'wagmi'
import { Avatar, AvatarImage, AvatarFallback } from '../ui/avatar'

interface EnsAddressResolverResult {
    address: `0x${string}` | null | undefined
    isLoading: boolean
    isError: boolean
    isValidEns: boolean
}

/**
 * Hook to resolve an ENS name to an Ethereum address.
 * Automatically detects if the input is an ENS name (contains '.eth').
 */
export function useEnsAddressResolver(nameOrAddress: string): EnsAddressResolverResult {
    const isValidEns = nameOrAddress.includes('.eth')

    const { data: address, isLoading, isError } = useEnsAddress({
        name: nameOrAddress,
        chainId: 1,
        query: { enabled: isValidEns }
    })

    return { address, isLoading, isError, isValidEns }
}

interface EnsAddressDisplayProps {
    /** ENS name to resolve and display */
    name: string
    /** Whether to show the avatar */
    showAvatar?: boolean
    /** Custom class name for styling */
    className?: string
}

/**
 * Displays a resolved ENS address with optional avatar.
 * Useful for showing who an ENS name resolves to.
 */
export function EnsAddressDisplay({ name, showAvatar = true, className = '' }: EnsAddressDisplayProps) {
    const { data: address, isLoading: addressLoading } = useEnsAddress({
        name,
        chainId: 1,
        query: { enabled: name.includes('.eth') }
    })

    const { data: avatar, isLoading: avatarLoading } = useEnsAvatar({
        name,
        chainId: 1
    })

    const isLoading = addressLoading || avatarLoading
    const truncatedAddress = address ? `${address.slice(0, 6)}...${address.slice(-4)}` : null

    return (
        <div className={`flex items-center gap-2 ${className}`}>
            {showAvatar && (
                <Avatar className="h-8 w-8">
                    {avatar && <AvatarImage src={avatar} alt={name} />}
                    <AvatarFallback className="bg-gradient-to-br from-secondary/20 to-secondary/40 text-secondary-foreground text-xs font-medium">
                        {name.slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                </Avatar>
            )}
            <div className="flex flex-col">
                <span className="font-medium">{name}</span>
                <span className={`text-xs text-muted-foreground ${isLoading ? 'animate-pulse' : ''}`}>
                    {isLoading ? 'Resolving...' : truncatedAddress ?? 'Not found'}
                </span>
            </div>
        </div>
    )
}
