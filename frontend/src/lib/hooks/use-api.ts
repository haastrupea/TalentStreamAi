"use client";

import { useAuth } from "@clerk/react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type {
  Application,
  DashboardStats,
  Entitlements,
  Profile,
  Resume,
  TailorRequest,
  TailorResponse,
} from "@/lib/types";

function useAuthedFetch() {
  const { getToken } = useAuth();

  return async function authedFetch<T>(
    path: string,
    init?: Parameters<typeof apiFetch>[1],
  ): Promise<T> {
    const token = await getToken();
    return apiFetch<T>(path, { ...init, token });
  };
}

export function useProfile(
  opts?: Omit<UseQueryOptions<Profile>, "queryKey" | "queryFn">,
) {
  const fetcher = useAuthedFetch();
  return useQuery<Profile>({
    queryKey: ["profile"],
    queryFn: () => fetcher<Profile>("/api/v1/profile"),
    ...opts,
  });
}

export function useEntitlements() {
  const fetcher = useAuthedFetch();
  return useQuery<Entitlements>({
    queryKey: ["entitlements"],
    queryFn: () => fetcher<Entitlements>("/api/v1/entitlements"),
  });
}

export function useDashboardStats() {
  const fetcher = useAuthedFetch();
  return useQuery<DashboardStats>({
    queryKey: ["dashboard-stats"],
    queryFn: () => fetcher<DashboardStats>("/api/v1/dashboard/stats"),
  });
}

export function useApplications() {
  const fetcher = useAuthedFetch();
  return useQuery<Application[]>({
    queryKey: ["applications"],
    queryFn: () => fetcher<Application[]>("/api/v1/applications"),
  });
}

export function useApplication(id: string | undefined) {
  const fetcher = useAuthedFetch();
  return useQuery<Application | undefined>({
    queryKey: ["application", id],
    enabled: Boolean(id),
    queryFn: () => fetcher<Application>(`/api/v1/applications/${id}`),
  });
}

export function useResumes() {
  const fetcher = useAuthedFetch();
  return useQuery<Resume[]>({
    queryKey: ["resumes"],
    queryFn: () => fetcher<Resume[]>("/api/v1/resumes"),
  });
}

export function useResume(id: string | undefined) {
  const fetcher = useAuthedFetch();
  return useQuery<Resume | undefined>({
    queryKey: ["resume", id],
    enabled: Boolean(id),
    queryFn: () => fetcher<Resume>(`/api/v1/resumes/${id}`),
  });
}

export function useTailorApplication() {
  const fetcher = useAuthedFetch();
  const queryClient = useQueryClient();

  return useMutation<TailorResponse, Error, TailorRequest>({
    mutationFn: (payload) =>
      fetcher<TailorResponse>("/api/v1/applications/tailor", {
        method: "POST",
        body: payload,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["application", data.applicationId] });
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      queryClient.invalidateQueries({ queryKey: ["entitlements"] });
    },
  });
}

export function useUploadBaseResume() {
  const fetcher = useAuthedFetch();
  const queryClient = useQueryClient();

  return useMutation<Resume, Error, File>({
    mutationFn: async (file) => {
      const form = new FormData();
      form.append("file", file);
      return fetcher<Resume>("/api/v1/profile/base-resume", {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      queryClient.invalidateQueries({ queryKey: ["resume"] });
      queryClient.invalidateQueries({ queryKey: ["entitlements"] });
    },
  });
}

/** Upload a resume file without making it the profile base (see POST /api/v1/resumes). */
export function useUploadResume() {
  const fetcher = useAuthedFetch();
  const queryClient = useQueryClient();

  return useMutation<Resume, Error, File>({
    mutationFn: async (file) => {
      const form = new FormData();
      form.append("file", file);
      return fetcher<Resume>("/api/v1/resumes", {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      queryClient.invalidateQueries({ queryKey: ["resume"] });
      queryClient.invalidateQueries({ queryKey: ["entitlements"] });
    },
  });
}

export function useSetBaseResume() {
  const fetcher = useAuthedFetch();
  const queryClient = useQueryClient();

  return useMutation<Profile, Error, string>({
    mutationFn: (resumeId) =>
      fetcher<Profile>("/api/v1/profile", {
        method: "PATCH",
        body: { baseResumeId: resumeId },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      queryClient.invalidateQueries({ queryKey: ["resumes"] });
      queryClient.invalidateQueries({ queryKey: ["resume"] });
    },
  });
}
