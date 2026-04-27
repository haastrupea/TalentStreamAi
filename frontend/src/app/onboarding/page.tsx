"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { UserButton } from "@clerk/react";
import { ArrowRight, Loader2, Upload } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getErrorMessage } from "@/lib/error-message";
import { useEntitlements, useUploadBaseResume } from "@/lib/hooks/use-api";
import { toast } from "sonner";

const ACCEPTED = ".pdf,.doc,.docx,.txt";

export default function OnboardingPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const { data: entitlements } = useEntitlements();
  const upload = useUploadBaseResume();
  const baseUploadsRemaining = Math.max(
    0,
    (entitlements?.limits.monthlyBaseResumeLimit ?? 0) -
      (entitlements?.usage.baseResumeUploads ?? 0),
  );

  function handlePick() {
    inputRef.current?.click();
  }

  function handleContinue() {
    if (!file) return;
    upload.mutate(file, {
      onSuccess: () => {
        router.push("/apply");
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <div className="flex min-h-screen flex-col bg-muted/30">
      <header className="border-b bg-background">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            TalentStream<span className="text-primary">AI</span>
          </Link>
          <UserButton />
        </div>
      </header>

      <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-12">
        <div className="space-y-2">
          <p className="text-sm font-medium text-primary">Step 1 of 1</p>
          <h1 className="text-3xl font-bold tracking-tight">
            Upload your base resume
          </h1>
          <p className="text-muted-foreground">
            We&apos;ll use this as the foundation for every tailored application.
            You can always update it later.
          </p>
        </div>

        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Base resume</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <button
              type="button"
              onClick={handlePick}
              disabled={baseUploadsRemaining <= 0}
              className="flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-10 transition-colors hover:bg-accent/40"
            >
              <Upload className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm font-medium">
                {file ? file.name : "Click to upload your resume"}
              </p>
              <p className="text-xs text-muted-foreground">
                PDF, DOC, DOCX, or TXT up to 10MB
              </p>
            </button>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED}
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />

            {upload.isError ? (
              <p className="text-sm text-destructive">
                {(upload.error as Error).message}
              </p>
            ) : null}
            {baseUploadsRemaining <= 0 ? (
              <p className="text-sm text-destructive">
                You have reached your monthly base resume upload limit for your current plan.
              </p>
            ) : null}

            <div className="flex items-center justify-between gap-3 pt-2">
              <Button asChild variant="ghost">
                <Link href="/dashboard">Skip for now</Link>
              </Button>
              <Button
                onClick={handleContinue}
                disabled={!file || upload.isPending || baseUploadsRemaining <= 0}
              >
                {upload.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    Continue
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
