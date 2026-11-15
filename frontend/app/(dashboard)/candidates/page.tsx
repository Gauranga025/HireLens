import { Header } from "@/components/layout/header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Upload, Users } from "lucide-react"

export default function CandidatesPage() {
  return (
    <div>
      <Header title="Candidates" subtitle="View and manage candidate profiles and resumes" />
      <main className="p-8 space-y-6">
      <div className="flex items-center justify-end">
        <Button>
          <Upload className="mr-2 h-4 w-4" />
          Upload Resume
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>No candidates yet</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <div className="text-center space-y-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <Users className="h-8 w-8 text-muted-foreground" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">Upload your first resume</h3>
              <p className="text-sm text-muted-foreground">
                Upload candidate resumes to begin the screening process
              </p>
            </div>
            <Button>
              <Upload className="mr-2 h-4 w-4" />
              Upload Resume
            </Button>
          </div>
        </CardContent>
      </Card>
      </main>
    </div>
  )
}
