"use client"

import { Header } from "@/components/layout/header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Briefcase, Users, FileCheck, TrendingUp } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const stats = [
  {
    title: "Active Jobs",
    value: "24",
    change: "+3 this month",
    icon: Briefcase,
  },
  {
    title: "Resumes Processed",
    value: "1,247",
    change: "+156 this week",
    icon: FileCheck,
  },
  {
    title: "Candidates Shortlisted",
    value: "89",
    change: "+12 this week",
    icon: Users,
  },
  {
    title: "Average Match Score",
    value: "78%",
    change: "+5% improvement",
    icon: TrendingUp,
  },
]

const chartData = [
  { name: "Mon", screened: 12, shortlisted: 4 },
  { name: "Tue", screened: 19, shortlisted: 7 },
  { name: "Wed", screened: 15, shortlisted: 5 },
  { name: "Thu", screened: 22, shortlisted: 8 },
  { name: "Fri", screened: 28, shortlisted: 11 },
  { name: "Sat", screened: 8, shortlisted: 3 },
  { name: "Sun", screened: 5, shortlisted: 2 },
]

const recentJobs = [
  { title: "Senior Python Developer", department: "Engineering", candidates: 45, status: "Active", date: "2024-01-15" },
  { title: "Product Manager", department: "Product", candidates: 32, status: "Active", date: "2024-01-14" },
  { title: "UX Designer", department: "Design", candidates: 28, status: "Active", date: "2024-01-13" },
  { title: "Data Scientist", department: "Data", candidates: 41, status: "Active", date: "2024-01-12" },
  { title: "DevOps Engineer", department: "Engineering", candidates: 23, status: "Paused", date: "2024-01-10" },
]

const recentActivity = [
  { name: "Sarah Johnson", job: "Senior Python Developer", score: 92, status: "Shortlisted" },
  { name: "Michael Chen", job: "Product Manager", score: 88, status: "Under Review" },
  { name: "Emily Davis", job: "UX Designer", score: 85, status: "Shortlisted" },
  { name: "James Wilson", job: "Data Scientist", score: 79, status: "Under Review" },
  { name: "Lisa Anderson", job: "Senior Python Developer", score: 76, status: "Under Review" },
]

export default function DashboardPage() {
  return (
    <div>
      <Header title="Dashboard" subtitle="Overview of your recruitment activity" />
      <main className="p-8 space-y-8">
      {/* Welcome Section */}
      <div>
        <h2 className="text-2xl font-bold text-foreground">Welcome back, John</h2>
        <p className="text-muted-foreground">Here&apos;s what&apos;s happening with your recruitment today.</p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-foreground">{stat.value}</div>
                <p className="text-xs text-muted-foreground">{stat.change}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Charts */}
      <Card>
        <CardHeader>
          <CardTitle>Screening Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--background))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                />
                <Bar dataKey="screened" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                <Bar dataKey="shortlisted" fill="hsl(var(--primary))" fillOpacity={0.5} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Tables */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job Title</TableHead>
                  <TableHead>Candidates</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentJobs.map((job) => (
                  <TableRow key={job.title}>
                    <TableCell>
                      <div>
                        <div className="font-medium text-foreground">{job.title}</div>
                        <div className="text-xs text-muted-foreground">{job.department}</div>
                      </div>
                    </TableCell>
                    <TableCell>{job.candidates}</TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                          job.status === "Active"
                            ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                            : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                        }`}
                      >
                        {job.status}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Candidate Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Candidate</TableHead>
                  <TableHead>Job</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentActivity.map((activity) => (
                  <TableRow key={activity.name}>
                    <TableCell className="font-medium text-foreground">{activity.name}</TableCell>
                    <TableCell className="text-muted-foreground">{activity.job}</TableCell>
                    <TableCell>
                      <span className="font-semibold text-foreground">{activity.score}%</span>
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                          activity.status === "Shortlisted"
                            ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                            : "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                        }`}
                      >
                        {activity.status}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
      </main>
    </div>
  )
}
