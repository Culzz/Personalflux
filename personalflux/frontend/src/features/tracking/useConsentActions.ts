import { customerApi } from "../../lib/endpoints";
import { useAuth } from "../auth/AuthContext";
import { useConsent } from "../consent/ConsentContext";

/** Changes the browser choice and, for signed-in users, the account setting too. */
export function useConsentActions() {
  const { user, updateUser } = useAuth();
  const { setConsent } = useConsent();

  async function sync(on: boolean) {
    if (!user || user.tracking_consent === on) return;
    try {
      updateUser(await customerApi.updateSettings(on));
    } catch {
      /* the browser choice still applies; the account setting can be retried in Settings */
    }
  }

  return {
    async allow() {
      setConsent("granted"); // first, so the session id exists for the next request
      await sync(true);
    },
    async deny() {
      await sync(false); // while the session still works
      setConsent("denied");
    },
  };
}
