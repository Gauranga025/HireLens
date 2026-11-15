import { Header } from "@/components/layout/header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FileText } from "lucide-react"

export default function ScreeningPage() {
  return (
    <div>
      <Header title="Screening Results" subtitle="View AI-powered candidate screening results" />
      <main className="p-8 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>No screening results yet</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <div className="text-center space-y-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <FileText className="h-8 w-8 text-muted-foreground" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">Start screening candidates</h3>
              <p className="text-sm text-muted-foreground">
                Create jobs and upload resumes to generate screening results
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      </main>
    </div>
  )
}
