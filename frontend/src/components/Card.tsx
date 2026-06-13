interface CardProps {
  title: string
  value: string | number
  subtitle?: string
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
}

const variantClasses: Record<string, string> = {
  default: 'border-gray-200',
  success: 'border-green-300 bg-green-50',
  warning: 'border-yellow-300 bg-yellow-50',
  danger: 'border-red-300 bg-red-50',
  info: 'border-blue-300 bg-blue-50',
}

export default function Card({ title, value, subtitle, variant = 'default' }: CardProps) {
  return (
    <div className={`rounded-lg border ${variantClasses[variant]} bg-white p-4 shadow-sm`}>
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {subtitle && <p className="mt-0.5 text-xs text-gray-500">{subtitle}</p>}
    </div>
  )
}