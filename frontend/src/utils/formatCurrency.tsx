import { useMemo } from "react";
import { useConfigSystem, useUserInfo } from "rj-core";

const listCurrency =
    [
        {
            "label": "ARS",
            "value": "$",
        },
        {
            "label": "BDT",
            "value": "৳",
        },
        {
            "label": "BGN",
            "value": "лв",
        },
        {
            "label": "BRL",
            "value": "R$",
        },
        {
            "label": "CHF",
            "value": "CHf",
        },
        {
            "label": "CLP",
            "value": "$",
        },
        {
            "label": "CNY",
            "value": "¥",
        },
        {
            "label": "COP",
            "value": "$",
        },
        {
            "label": "CZK",
            "value": "Kč",
        },
        {
            "label": "EUR",
            "value": "€",
        },
        {
            "label": "GBP",
            "value": "£",
        },
        {
            "label": "HKD",
            "value": "HK$",
        },
        {
            "label": "HRK",
            "value": "kn",
        },
        {
            "label": "HUF",
            "value": "Ft",
        },
        {
            "label": "IDR",
            "value": "Rp",
        },
        {
            "label": "INR",
            "value": "₹",
        },
        {
            "label": "JPY",
            "value": "¥",
        },
        {
            "label": "KRW",
            "value": "₩",
        },
        {
            "label": "MXN",
            "value": "$",
        },
        {
            "label": "MYR",
            "value": "RM",
        },
        {
            "label": "NOK",
            "value": "kr",
        },
        {
            "label": "NPR",
            "value": "₨",
        },
        {
            "label": "PEN",
            "value": "S/",
        },
        {
            "label": "PHP",
            "value": "₱",
        },
        {
            "label": "PKR",
            "value": "₨",
        },
        {
            "label": "PLN",
            "value": "zł",
        },
        {
            "label": "SEK",
            "value": "kr",
        },
        {
            "label": "SGD",
            "value": "S$",
        },
        {
            "label": "THB",
            "value": "฿",
        },
        {
            "label": "USD",
            "value": "$",
        },
        {
            "label": "VND",
            "value": "₫",
        }
    ]

export const formatCurrency = () => {
    const userInfo = useUserInfo();
    const [configSystem] = useConfigSystem();
    const unitPreferences =
        configSystem && configSystem['system_default_formats'];
    console.log("unitPreferences", unitPreferences)


    const currencyFormat = useMemo(() => {
        return (userInfo as { settings?: { currency_format__name?: string } })?.settings?.currency_format__name ?? unitPreferences?.currency_format__name ?? 'USD';
    }, [userInfo, unitPreferences]);
    const currencySymbol = useMemo(() => {
        const currencyName = (userInfo as { settings?: { currency_format__name?: string } })?.settings?.currency_format__name ??
            unitPreferences?.currency_format ?? 'USD';
        const currencySymboldata = listCurrency.filter((item: any) => item.label === currencyName)[0]?.value ?? '$';
        return currencySymboldata ?? '$';
    }, [userInfo, unitPreferences]);

    return { currencyFormat, currencySymbol, listCurrency };
};


export const formatCurrencyPlacement = (data: string, currencySymbol: string, position: string = 'after') => {
    if (position === 'before') {
        return `${currencySymbol} ${data}`;
    }
    return `${data} ${currencySymbol}`;
};

export const useFormatCurrencyPlacement = () => {
    const userInfo = useUserInfo();
    const [configSystem] = useConfigSystem();
    const unitPreferences =
        configSystem && configSystem['system_default_formats'];
    const position = (userInfo as { settings?: { currency_symbol_placement?: string } })?.settings?.currency_symbol_placement ?? unitPreferences?.symbol_placement ?? 'after';

    const format = (data: string, currencySymbol: string) => {
        return formatCurrencyPlacement(data, currencySymbol, position);
    };

    return { format, position };
};