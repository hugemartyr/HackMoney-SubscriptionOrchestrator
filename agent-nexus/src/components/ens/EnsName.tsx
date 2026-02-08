import { useEnsName } from 'wagmi'
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip"

interface EnsNameProps {
    /** The Ethereum address to resolve */
    address: `0x${string}` | string | undefined | null
    /** Optional custom class name */
    className?: string
    /** Whether to show the full address in a tooltip on hover */
    showTooltip?: boolean
}

/**
 * A lightweight component to display an ENS name for a given address.
 * Falls back to truncated address if no ENS name is found.
 * 
 * Usage:
 * <EnsName address="0x123..." />
 */
export function EnsName({ address, className = '', showTooltip = true }: EnsNameProps) {
    // Safe handling for undefined/null/invalid strings
    const validAddress = address && address.startsWith('0x') ? (address as `0x${string}`) : undefined

    const { data: name, isLoading } = useEnsName({
        address: validAddress,
        chainId: 1
    })

    if (!address) return null

    const truncated = address.length > 10
        ? `${address.slice(0, 6)}...${address.slice(-4)}`
        : address

    const display = isLoading ? (
        <span className="animate-pulse bg-secondary/50 rounded px-1">...</span>
    ) : (
        name ?? truncated
    )

    const content = (
        <span className={`font-medium ${className}`}>
            {display}
        </span>
    )

    if (showTooltip && (name || truncated !== address)) {
        return (
            <TooltipProvider>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <span className="cursor-help underline decoration-dotted decoration-muted-foreground/30 underline-offset-2">
                            {content}
                        </span>
                    </TooltipTrigger>
                    <TooltipContent>
                        <p className="font-mono text-xs">{address}</p>
                    </TooltipContent>
                </Tooltip>
            </TooltipProvider>
        )
    }

    return content
}
