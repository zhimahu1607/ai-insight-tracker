import { DailyChart } from "@/components/business/DailyChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useFileList } from "@/hooks/queries/use-file-list";
import { FileText, Newspaper, BarChart2, Activity } from "lucide-react";

export function HomePage() {
  const { data: fileList } = useFileList();

  const stats = [
    {
      title: "Total Papers Days",
      value: fileList?.papers?.length ?? 0,
      icon: FileText,
      description: "Days with analyzed papers",
    },
    {
      title: "Total News Days",
      value: fileList?.news?.length ?? 0,
      icon: Newspaper,
      description: "Days with collected news",
    },
    {
      title: "Generated Reports",
      value: fileList?.reports?.length ?? 0,
      icon: BarChart2,
      description: "Daily summaries generated",
    },
    {
      title: "Last Updated",
      value: fileList?.last_updated ? new Date(fileList.last_updated).toLocaleDateString() : "-",
      icon: Activity,
      description: "System last update time",
    },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <DailyChart />
    </div>
  );
}
