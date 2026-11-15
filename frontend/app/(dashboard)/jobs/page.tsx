import { Header } from "@/components/layout/header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, Briefcase } from "lucide-react"

export default function JobsPage() {
  return (
    <div>
      <Header title="Jobs" subtitle="Manage your job postings and requirements" />
      <main className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create Job
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>No jobs yet</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <div className="text-center space-y-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <Briefcase className="h-8 w-8 text-muted-foreground" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">Create your first job posting</h3>
              <p className="text-sm text-muted-foreground">
                Start by creating a job description to begin screening candidates
              </p>
            </div>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Job
            </Button>
          </div>
        </CardContent>
      </Card>
      </main>
    </div>
  )
}
