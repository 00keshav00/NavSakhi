import { Card, CardContent } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: "up" | "down" | "neutral";
}

export function MetricCard({ title, value, subtitle, icon: Icon, trend }: MetricCardProps) {
  return (
    <Card className="overflow-hidden border-border bg-card shadow-sm transition-all hover:shadow-md">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-col space-y-1">
            <span className="text-sm font-medium text-muted-foreground">{title}</span>
            <span className="text-2xl font-bold text-foreground">{value}</span>
            {subtitle && (
              <span className="text-xs text-muted-foreground">{subtitle}</span>
            )}
          </div>
          <div className="rounded-xl bg-primary/10 p-3 text-primary">
            <Icon size={24} strokeWidth={2} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}