import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { Tabs } from '@/components/Form/Tabs';

import { ContentSection } from '../types/operationalNotice.types';
import CustomTiptap from './CustomTipTap';

interface CustomTiptapWithTabsProps {
  contentSections?: ContentSection[];
  onChange?: (sections: ContentSection[]) => void;
  onValidationChange?: (isValid: boolean) => void;
  heightContent?: string;
  includeStyles?: boolean;
}

const CustomTiptapWithTabs: React.FC<CustomTiptapWithTabsProps> = ({
  contentSections = [],
  onChange,
  onValidationChange,
  heightContent = '500px',
  includeStyles = false,
}) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState(0);

  const defaultSections: ContentSection[] = [
    { id: '1', title: t('Content 1'), content: '' },
    { id: '2', title: t('Content 2'), content: '' },
    { id: '3', title: t('Content 3'), content: '' },
  ];

  const sections =
    contentSections.length > 0 ? contentSections : defaultSections;

  const updateSectionContent = (sectionId: string, content: string) => {
    const updatedSections = sections.map((section) =>
      section.id === sectionId ? { ...section, content } : section,
    );
    onChange?.(updatedSections);
    checkValidation(updatedSections);
  };

  const hasValidContent = (content: string): boolean => {
    if (!content || content.trim() === '') return false;
    const invalidPatterns = [
      '<p><br class="ProseMirror-trailingBreak"></p></div></div>',
      '<p></p>',
      '<p><br></p>',
      ' padding: 4px;border-radius: 8px;"><p><br class="ProseMirror-trailingBreak"></p></div></div>',
    ];
    return !invalidPatterns.some((pattern) => content.includes(pattern));
  };

  const checkValidation = (sectionsToCheck: ContentSection[]) => {
    const isValid = sectionsToCheck.some((section) =>
      hasValidContent(section.content || ''),
    );
    onValidationChange?.(isValid);
  };

  useEffect(() => {
    checkValidation(sections);
  }, [sections, contentSections]);

  const currentSection = sections[activeTab];

  return (
    <div
      className="custom-tiptap-with-tabs"
      style={{ height: heightContent }}
    >
      <Tabs
        items={sections.map((section) => ({
          label: section.title,
          content: '',
        }))}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
      <div className="tab-content">
        {currentSection && (
          <CustomTiptap
            content={currentSection.content || ''}
            onChange={(value) => updateSectionContent(currentSection.id, value)}
            label=""
            heightContent={`calc(${heightContent} - 120px)`}
            includeStyles={includeStyles}
          />
        )}
      </div>
    </div>
  );
};

export default CustomTiptapWithTabs;
