import React from 'react';
import { render, screen } from '@testing-library/react';
import GalleryView from './GalleryView';

const mockFolders = {
  'TestFolderA': [
    { url: 'https://example.com/img1.jpg', name: 'img1', mimetype: 'image/jpeg', folder: 'TestFolderA', location_tag: 'Paris' },
    { url: 'https://example.com/img2.jpg', name: 'img2', mimetype: 'image/jpeg', folder: 'TestFolderA', location_tag: 'London' }
  ],
  'TestFolderB': [
    { url: 'https://example.com/img3.jpg', name: 'img3', mimetype: 'image/jpeg', folder: 'TestFolderB', location_tag: 'Berlin' }
  ],
  'EmptyFolder': []
};

describe('GalleryView', () => {
  test('auto-selects the first folder with images and displays them', () => {
    render(<GalleryView folders={mockFolders} />);
    // Images from TestFolderA should be displayed
    expect(screen.getByAltText('img1')).toBeInTheDocument();
    expect(screen.getByAltText('img2')).toBeInTheDocument();
    expect(screen.queryByAltText('img3')).not.toBeInTheDocument();
    // The folder dropdown should have TestFolderA selected
    const select = screen.getByLabelText(/select folder/i);
    expect(select.value).toBe('TestFolderA');
  });

  test('shows correct message when all folders are empty', () => {
    render(<GalleryView folders={{ EmptyFolder: [] }} />);
    expect(screen.getByText(/no images found/i)).toBeInTheDocument();
  });

  test('switches folder and displays correct images', () => {
    render(<GalleryView folders={mockFolders} />);
    // Change folder selection
    const select = screen.getByLabelText(/select folder/i);
    // Simulate selecting TestFolderB
    select.value = 'TestFolderB';
    select.dispatchEvent(new Event('change', { bubbles: true }));
    expect(screen.getByAltText('img3')).toBeInTheDocument();
    expect(screen.queryByAltText('img1')).not.toBeInTheDocument();
  });
});
