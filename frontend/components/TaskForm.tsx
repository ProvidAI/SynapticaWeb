'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useTaskStore } from '@/store/taskStore'
import { Send } from 'lucide-react'

interface TaskFormProps {
  onSubmit: (description: string) => void
}

export function TaskForm({ onSubmit }: TaskFormProps) {
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const { setDescription: setTaskDescription, setUploadedFile, status } = useTaskStore()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      setUploadedFile(selectedFile)
    }
  }

  const handleSubmit = () => {
    if (!description.trim()) {
      alert('Please enter a task description')
      return
    }

    setTaskDescription(description)
    onSubmit(description)
  }

  const isDisabled = status !== 'IDLE' && status !== 'FAILED'

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create New Task</CardTitle>
        <CardDescription>
          Describe what you need an AI agent to complete
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="description" className="text-sm font-medium">
            Task Description
          </label>
          <Textarea
            id="description"
            placeholder="e.g., Analyze my sales_data.csv file. I need to know the total monthly revenue and a list of the top 5 selling products."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isDisabled}
            rows={6}
            className="resize-none"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="file" className="text-sm font-medium">
            Upload File (Optional)
          </label>
          <div className="flex items-center gap-2">
            <Input
              id="file"
              type="file"
              onChange={handleFileChange}
              disabled={isDisabled}
              className="cursor-pointer"
            />
            {file && (
              <span className="text-sm text-muted-foreground">
                {file.name}
              </span>
            )}
          </div>
        </div>

        <Button
          onClick={handleSubmit}
          disabled={isDisabled || !description.trim()}
          className="w-full"
        >
          <Send className="mr-2 h-4 w-4" />
          Start Task
        </Button>
      </CardContent>
    </Card>
  )
}

