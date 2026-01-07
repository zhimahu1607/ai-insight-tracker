import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const data = [
  {
    date: "Jan 01",
    papers: 45,
    news: 80,
  },
  {
    date: "Jan 02",
    papers: 52,
    news: 98,
  },
  {
    date: "Jan 03",
    papers: 48,
    news: 90,
  },
  {
    date: "Jan 04",
    papers: 61,
    news: 105,
  },
  {
    date: "Jan 05",
    papers: 55,
    news: 85,
  },
  {
    date: "Jan 06",
    papers: 67,
    news: 110,
  },
  {
    date: "Jan 07",
    papers: 60,
    news: 100,
  },
];

export function DailyChart() {
  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle>Activity Trends</CardTitle>
        <CardDescription>
          Number of analyzed papers and news items over the last 7 days.
        </CardDescription>
      </CardHeader>
      <CardContent className="pl-2">
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#888888"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${value}`}
            />
            <Tooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="papers"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              activeDot={{ r: 6 }}
              name="Papers"
            />
             <Line
              type="monotone"
              dataKey="news"
              stroke="hsl(var(--chart-2))"
              strokeWidth={2}
              activeDot={{ r: 6 }}
              name="News"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

