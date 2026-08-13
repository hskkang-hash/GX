import { useMemo } from "react";
import { useConfigSystem, useUserInfo } from "rj-core";
import {
    formatNumber as formatNumberUtil,
    type NumberFormatConfig,
} from "./formatNumberUtils";
import { IUserInfo } from "@/types/form";

/**
 * Hook to get number formatting functions with configSystem
 * @returns Functions to format and parse numbers based on system config
 */
export const useFormatNumber = () => {
    const [configSystem] = useConfigSystem();
    const userInfo = useUserInfo() as IUserInfo;

    const formatConfig: NumberFormatConfig = useMemo(
        () => ({
            number_format: userInfo?.settings?.number_format__name ?? configSystem?.system_default_formats?.number_format__name,
            decimal_places: userInfo?.settings?.decimal_places ?? configSystem?.system_default_formats?.decimal_places,
        }),
        [configSystem, userInfo]
    );

    const formatNumber = useMemo(
        () => (value: number | string | null | undefined) => {
            return formatNumberUtil(value, formatConfig);
        },
        [formatConfig]
    );

    return {
        formatNumber,
    };
};

