import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  createProfile as createProfileApi,
  deleteProfile as deleteProfileApi,
  listProfiles,
} from '@/services/api';
import type { SavedScan, UserProfile } from '@/types/smartfit';

interface ProfileContextValue {
  profiles: UserProfile[];
  activeProfileId: string;
  activeProfile: UserProfile;
  setActiveProfileId: (profileId: string) => void;
  createProfile: (name: string) => Promise<string>;
  saveScan: (profileId: string, scan: Omit<SavedScan, 'id'>) => void;
  exportData: () => string;
  deleteAllData: () => void;
}

const ProfileContext = createContext<ProfileContextValue | undefined>(undefined);

const STORAGE_KEYS = {
  profiles: 'smartfit-profiles',
  activeProfileId: 'smartfit-active-profile-id',
};

const createDefaultProfile = (): UserProfile => ({
  id: 'profile-local-primary',
  name: 'Primary Profile',
  createdAt: new Date().toISOString(),
  scans: [],
});

const loadProfiles = (): UserProfile[] => {
  const raw = localStorage.getItem(STORAGE_KEYS.profiles);

  if (!raw) {
    return [createDefaultProfile()];
  }

  try {
    const parsed = JSON.parse(raw) as UserProfile[];

    if (!Array.isArray(parsed) || parsed.length === 0) {
      return [createDefaultProfile()];
    }

    return parsed;
  } catch {
    return [createDefaultProfile()];
  }
};

const loadActiveProfileId = (): string => {
  return localStorage.getItem(STORAGE_KEYS.activeProfileId) || 'profile-local-primary';
};

export const ProfileProvider = ({ children }: { children: ReactNode }) => {
  const [profiles, setProfiles] = useState<UserProfile[]>(loadProfiles);
  const [activeProfileId, setActiveProfileIdState] = useState<string>(loadActiveProfileId);

  const persistProfiles = useCallback((nextProfiles: UserProfile[]) => {
    setProfiles(nextProfiles);
    localStorage.setItem(STORAGE_KEYS.profiles, JSON.stringify(nextProfiles));
  }, []);

  useEffect(() => {
    let isMounted = true;

    const syncProfilesFromBackend = async () => {
      try {
        let remoteProfiles = await listProfiles();

        if (remoteProfiles.length === 0) {
          const created = await createProfileApi('Primary Profile');
          remoteProfiles = [created];
        }

        if (!isMounted) {
          return;
        }

        const localScanLookup = new Map(profiles.map((profile) => [profile.id, profile.scans]));
        const mergedProfiles = remoteProfiles.map((profile) => ({
          ...profile,
          scans: localScanLookup.get(profile.id) || [],
        }));

        persistProfiles(mergedProfiles);
        setActiveProfileIdState((currentId) => {
          const resolvedId = mergedProfiles.some((profile) => profile.id === currentId)
            ? currentId
            : mergedProfiles[0].id;

          localStorage.setItem(STORAGE_KEYS.activeProfileId, resolvedId);
          return resolvedId;
        });
      } catch {
        // Keep local profiles when backend profile sync is unavailable.
      }
    };

    void syncProfilesFromBackend();

    return () => {
      isMounted = false;
    };
  }, [persistProfiles]);

  const setActiveProfileId = useCallback(
    (profileId: string) => {
      const profileExists = profiles.some((profile) => profile.id === profileId);

      if (!profileExists) {
        return;
      }

      setActiveProfileIdState(profileId);
      localStorage.setItem(STORAGE_KEYS.activeProfileId, profileId);
    },
    [profiles]
  );

  const createProfile = useCallback(
    async (name: string) => {
      const trimmedName = name.trim() || `Profile ${profiles.length + 1}`;

      try {
        const newProfile = await createProfileApi(trimmedName);
        const nextProfiles = [{ ...newProfile, scans: [] }, ...profiles];
        persistProfiles(nextProfiles);
        setActiveProfileIdState(newProfile.id);
        localStorage.setItem(STORAGE_KEYS.activeProfileId, newProfile.id);
        return newProfile.id;
      } catch {
        const profileId = `profile-local-${Date.now()}`;
        const fallbackProfile: UserProfile = {
          id: profileId,
          name: trimmedName,
          createdAt: new Date().toISOString(),
          scans: [],
        };

        const nextProfiles = [fallbackProfile, ...profiles];
        persistProfiles(nextProfiles);
        setActiveProfileIdState(profileId);
        localStorage.setItem(STORAGE_KEYS.activeProfileId, profileId);
        return profileId;
      }
    },
    [profiles, persistProfiles]
  );

  const saveScan = useCallback(
    (profileId: string, scan: Omit<SavedScan, 'id'>) => {
      const nextProfiles = profiles.map((profile) => {
        if (profile.id !== profileId) {
          return profile;
        }

        const nextScan: SavedScan = {
          ...scan,
          id: `scan-${Date.now()}-${Math.round(Math.random() * 1000)}`,
        };

        return {
          ...profile,
          scans: [nextScan, ...profile.scans].slice(0, 24),
        };
      });

      persistProfiles(nextProfiles);
    },
    [profiles, persistProfiles]
  );

  const exportData = useCallback(() => {
    return JSON.stringify(
      {
        exportedAt: new Date().toISOString(),
        profiles,
      },
      null,
      2
    );
  }, [profiles]);

  const deleteAllData = useCallback(() => {
    const resetProfiles = async () => {
      await Promise.all(
        profiles.map((profile) => deleteProfileApi(profile.id).catch(() => undefined))
      );

      try {
        const fallback = [await createProfileApi('Primary Profile')];
        persistProfiles(fallback);
        setActiveProfileIdState(fallback[0].id);
        localStorage.setItem(STORAGE_KEYS.activeProfileId, fallback[0].id);
      } catch {
        const fallback = [createDefaultProfile()];
        persistProfiles(fallback);
        setActiveProfileIdState(fallback[0].id);
        localStorage.setItem(STORAGE_KEYS.activeProfileId, fallback[0].id);
      }
    };

    void resetProfiles();
  }, [persistProfiles, profiles]);

  const activeProfile = useMemo(() => {
    return profiles.find((profile) => profile.id === activeProfileId) || profiles[0] || createDefaultProfile();
  }, [profiles, activeProfileId]);

  const value = useMemo(
    () => ({
      profiles,
      activeProfileId: activeProfile.id,
      activeProfile,
      setActiveProfileId,
      createProfile,
      saveScan,
      exportData,
      deleteAllData,
    }),
    [profiles, activeProfile.id, activeProfile, setActiveProfileId, createProfile, saveScan, exportData, deleteAllData]
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
};

export const useProfiles = (): ProfileContextValue => {
  const context = useContext(ProfileContext);

  if (!context) {
    throw new Error('useProfiles must be used inside ProfileProvider');
  }

  return context;
};
