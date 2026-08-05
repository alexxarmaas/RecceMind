import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, TextInput } from 'react-native';
import { BlurView } from 'expo-blur';
import { FontAwesome5 } from '@expo/vector-icons';

export interface PacenoteItem {
  type: 'distance' | 'note';
  text: string;
  curve_index: number | null;
}

interface PacenoteListProps {
  notes: PacenoteItem[];
  onNotePress?: (curveIndex: number) => void;
  selectedCurveIndex?: number | null;
  onNoteEdit?: (index: number, newText: string) => void;
}

const PacenoteList: React.FC<PacenoteListProps> = ({ notes, onNotePress, selectedCurveIndex, onNoteEdit }) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState('');

  const handleEditStart = (index: number, text: string) => {
    setEditingIndex(index);
    setEditText(text);
  };

  const handleSave = (index: number) => {
    if (onNoteEdit) {
      onNoteEdit(index, editText);
    }
    setEditingIndex(null);
  };
  if (!notes || notes.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>No hay notas disponibles.</Text>
      </View>
    );
  }

  return (
    <BlurView intensity={80} tint="dark" style={styles.container}>
      <Text style={styles.title}>
         <FontAwesome5 name="clipboard-list" size={18} color="#fff" /> Notas de Ruta (Pacenotes)
      </Text>
      <FlatList
        data={notes}
        keyExtractor={(item, index) => index.toString()}
        renderItem={({ item, index }) => {
          const isSelected = item.curve_index !== null && item.curve_index === selectedCurveIndex;
          const isEditing = editingIndex === index;
          
          if (isEditing) {
            return (
              <View style={[styles.noteItem, styles.editingContainer]}>
                <TextInput
                  style={styles.editInput}
                  value={editText}
                  onChangeText={setEditText}
                  autoFocus
                />
                <View style={styles.editActions}>
                  <TouchableOpacity onPress={() => handleSave(index)} style={styles.saveBtn}>
                    <FontAwesome5 name="check" size={16} color="#fff" />
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => setEditingIndex(null)} style={styles.cancelBtn}>
                    <FontAwesome5 name="times" size={16} color="#fff" />
                  </TouchableOpacity>
                </View>
              </View>
            );
          }

          return (
            <TouchableOpacity 
              style={[
                styles.noteItem, 
                item.type === 'distance' ? styles.distanceItem : styles.curveItem,
                isSelected && styles.selectedItem
              ]}
              disabled={item.curve_index === null}
              onPress={() => item.curve_index !== null && onNotePress && onNotePress(item.curve_index)}
            >
              <View style={styles.noteContent}>
                <Text style={[
                  styles.noteText,
                  item.type === 'distance' && styles.distanceText,
                  isSelected && styles.selectedText,
                  item.text.includes('Derecha') && !isSelected && styles.rightText,
                  item.text.includes('Izquierda') && !isSelected && styles.leftText,
                ]}>
                  {item.type === 'distance' ? `${item.text}m` : item.text}
                </Text>
                
                {item.type === 'note' && (
                  <TouchableOpacity 
                    style={styles.editIconBtn} 
                    onPress={() => handleEditStart(index, item.text)}
                  >
                    <FontAwesome5 name="pen" size={12} color={isSelected ? "#fff" : "#888"} />
                  </TouchableOpacity>
                )}
              </View>
            </TouchableOpacity>
          );
        }}
      />
    </BlurView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    borderRadius: 24,
    padding: 20,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.15)',
    backgroundColor: 'rgba(20,20,20,0.4)', // Base glass effect
  },
  title: {
    fontSize: 18,
    fontFamily: 'Inter_700Bold',
    marginBottom: 20,
    textAlign: 'center',
    color: '#fff',
    letterSpacing: 1.5,
  },
  noteItem: {
    padding: 18,
    borderRadius: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  distanceItem: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    padding: 10,
    alignItems: 'center',
    borderColor: 'transparent',
    borderRadius: 12,
    marginHorizontal: 40,
  },
  curveItem: {
    backgroundColor: 'rgba(255,255,255,0.12)',
  },
  selectedItem: {
    backgroundColor: '#d60000',
    borderColor: '#ff4444',
    shadowColor: '#ff4444',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.8,
    shadowRadius: 15,
    elevation: 8,
    transform: [{ scale: 1.02 }],
  },
  noteText: {
    fontSize: 20,
    fontFamily: 'Inter_700Bold',
    color: '#fff',
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  rightText: {
    color: '#ff4444', // Neon Red for right
  },
  leftText: {
    color: '#33b5e5', // Neon Blue for left
  },
  distanceText: {
    fontSize: 14,
    color: '#aaa',
    fontFamily: 'Inter_400Regular',
  },
  selectedText: {
    color: '#ffffff',
  },
  emptyContainer: {
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  emptyText: {
    color: '#888',
    fontFamily: 'Inter_400Regular',
    marginTop: 10,
  },
  noteContent: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  editIconBtn: {
    position: 'absolute',
    right: 0,
    padding: 5,
  },
  editingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderColor: '#4da6ff',
  },
  editInput: {
    flex: 1,
    color: '#fff',
    fontFamily: 'Inter_700Bold',
    fontSize: 18,
    borderBottomWidth: 1,
    borderBottomColor: '#aaa',
    paddingVertical: 5,
    marginRight: 10,
  },
  editActions: {
    flexDirection: 'row',
  },
  saveBtn: {
    backgroundColor: '#00cc66',
    padding: 10,
    borderRadius: 8,
    marginRight: 5,
  },
  cancelBtn: {
    backgroundColor: '#d60000',
    padding: 10,
    borderRadius: 8,
  }
});

export default PacenoteList;
