import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { BsTrash } from 'react-icons/bs';
import { GoPlus } from 'react-icons/go';
import { FormBlock, useTheme } from 'rj-core';

import Colors from '../../configs/Colors';
import useAPI, { Command, Terminal } from '../../features/routes/useAPI/useAPI';
import CustomTextarea from '../Form/CustomTextarea';
import CustomSelect from '../selects/CustomSelect';
import PaginationSelect from '../selects/PaginationSelect';
import './CustomTabsForRoutes.scss';

const OPTIONS_COMMAND = [
  {
    label: 'MAV_CMD_DO_SET_SERVO',
    value: 'MAV_CMD_DO_SET_SERVO',
  },
  {
    label: 'MAV_CMD_DO_SET_ROI',
    value: 'MAV_CMD_DO_SET_ROI',
  },
  {
    label: 'MAV_CMD_DO_SET_ROI_LOCATION',
    value: 'MAV_CMD_DO_SET_ROI_LOCATION',
  },
  {
    label: 'MAV_CMD_DO_SET_ROI_LOCATION_EX',
    value: 'MAV_CMD_DO_SET_ROI_LOCATION_EX',
  },
];

const CustomTabsForRoutes: React.FC<{
  terminalId: number;
  indexTerminal: number;
}> = ({ terminalId, indexTerminal }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { control, setValue, watch } = useFormContext();
  const [selectedCMD, setSelectedCMD] = useState<Command | null>(null);
  const [indexCMD, setIndexCMD] = useState<number | null>(null);
  const { getOptionsCMD } = useAPI();

  const commandList = useMemo(() => {
    const currentTerminals = watch('terminals') || [];

    const currentTerminal = currentTerminals.find(
      (item: Terminal) => item.terminal_id === terminalId,
    );
    return (
      currentTerminal?.command || [
        {
          id: Date.now().toString(),
          name: `CMD ${currentTerminal?.command?.length + 1}`,
          key: null,
          value: '',
        },
      ]
    );
  }, [terminalId, watch('terminals')]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (commandList && commandList.length > 0) {
      setSelectedCMD(commandList[0]);
      setIndexCMD(0);
    } else {
      setSelectedCMD(null);
      setIndexCMD(null);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAddCommand = useCallback(() => {
    const newCMD = {
      id: Date.now().toString(),
      name: `CMD ${commandList.length + 1}`,
      key: null,
      value: '',
    };

    const updatedCommandList = [...commandList, newCMD];

    const updatedTerminals = watch('terminals').map((item: Terminal) =>
      item.terminal_id === terminalId
        ? { ...item, command: updatedCommandList }
        : item,
    );

    setValue('terminals', updatedTerminals);
    setSelectedCMD(newCMD);
    setIndexCMD(updatedCommandList.length - 1);
  }, [commandList, setValue, terminalId, watch]);

  const handleDeleteCommand = useCallback(
    (id: string) => {
      const newCMD: Command[] = [];
      let deletedIndex = -1;

      commandList.forEach((item: Command, index: number) => {
        if (item.id === id) {
          deletedIndex = index;
        } else {
          newCMD.push({
            ...item,
            name: `CMD ${newCMD.length + 1}`,
          });
        }
      });

      setSelectedCMD((currentSelected) => {
        if (!currentSelected) return null;

        if (currentSelected.id === id) {
          if (newCMD.length === 0) return null;

          const nextIndex = Math.min(deletedIndex, newCMD.length - 1);
          setIndexCMD(nextIndex);
          return newCMD[nextIndex];
        }

        return (
          newCMD
            .map((item: Command, index: number) => {
              if (item.id === currentSelected.id) {
                setIndexCMD(index);
              }
              return item;
            })
            .find((item: Command) => item.id === currentSelected.id) || null
        );
      });

      const updatedTerminals = watch('terminals').map((item: Terminal) =>
        item.terminal_id === terminalId ? { ...item, command: newCMD } : item,
      );

      setValue('terminals', updatedTerminals);
    },
    [commandList, setValue, terminalId, watch],
  );

  const handleValueChange = useCallback(
    (value: string) => {
      setSelectedCMD((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          value: value,
        };
      });

      const updatedCommandList = commandList.map((item: Command) =>
        item.id === selectedCMD?.id ? { ...item, value: value } : item,
      );

      const updatedTerminals = watch('terminals').map((item: Terminal) =>
        item.terminal_id === terminalId
          ? { ...item, command: updatedCommandList }
          : item,
      );

      setValue('terminals', updatedTerminals);
    },
    [selectedCMD?.id, commandList, setValue, terminalId, watch('terminals')], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const RenderRightPanel = useMemo(() => {
    if (!selectedCMD) return null;
    return (
      <FormBlock
        className="d-flex flex-column gap-3"
        key={selectedCMD?.id}
        style={{
          backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
          height: 'fit-content',
        }}
      >
        {/* <CustomSelect
          name={`terminals[${indexTerminal}].command[${indexCMD}].key`}
          control={control}
          options={OPTIONS_COMMAND}
          placeholder={t('Select Key')}
        /> */}
        <PaginationSelect
          required
          name={`terminals[${indexTerminal}].command[${indexCMD}].key`}
          control={control}
          loadOptions={getOptionsCMD()}
          placeholder={t('Select')}
        />
        <CustomTextarea
          control={control}
          name={`terminals[${indexTerminal}].command[${indexCMD}].value`}
          placeholder={t('Value')}
          className="command-textarea "
          customOnChange={handleValueChange}
          enableJsonFormat={true}
        />
      </FormBlock>
    );
  }, [control, selectedCMD, theme, t, handleValueChange, indexCMD]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <div
        style={{ gridColumn: 'span 2' }}
        id="custom-tabs-for-routes"
      >
        {/* <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            cursor: 'pointer',
            color: Colors.Primary,
            fontSize: '1rem',
            fontWeight: 600,
          }}
          onClick={handleAddCommand}
        >
          <GoPlus size={18} /> {t('Add More CMD')}
        </div> */}
        {commandList.length > 0 && (
          <div
            className="d-flex w-100 gap-3"
            style={{
              height: '20rem',
            }}
          >
            {/* leftPanel */}
            {/* <div
              className="d-flex flex-column gap-2 overflow-y-auto overflow-x-hidden"
              style={{
                scrollbarWidth: 'thin',
                scrollbarColor: theme === 'dark' ? '#293438' : '#EEF9FF',
                minWidth: 'fit-content',
              }}
            >
              {commandList.map((item: Command, index: number) => (
                <FormBlock
                  key={item.id}
                  style={{
                    backgroundColor:
                      selectedCMD?.id === item.id
                        ? theme === 'dark'
                          ? '#293438'
                          : '#EEF9FF'
                        : theme === 'dark'
                          ? '#2D2E30'
                          : '#F6F7F8',
                    width: '7.5rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '1rem',
                    borderRadius: '0.5rem',
                  }}
                  onClick={() => {
                    setSelectedCMD({
                      ...item,
                    });
                    setIndexCMD(index);
                  }}
                >
                  <div
                    style={{
                      color:
                        selectedCMD?.id === item.id ? Colors.Primary : 'unset',
                      fontWeight: selectedCMD?.id === item.id ? 600 : 400,
                    }}
                  >
                    {item.name}
                  </div>
                  <BsTrash
                    size={16}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteCommand(item.id);
                    }}
                  />
                </FormBlock>
              ))}
            </div> */}
            {/* rightPanel */}
            <div className="w-100">{RenderRightPanel}</div>
          </div>
        )}
      </div>
    </>
  );
};

export default CustomTabsForRoutes;
